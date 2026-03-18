import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';

import 'package:path_provider/path_provider.dart';

/// A single operation queued for later execution when connectivity returns.
class QueuedOperation {
  const QueuedOperation({
    required this.id,
    required this.type,
    required this.endpoint,
    required this.payload,
    required this.timestamp,
    this.attempts = 0,
  });

  /// Unique identifier for this queued operation.
  final String id;

  /// HTTP method or logical operation type (e.g. 'POST', 'PUT', 'DELETE').
  final String type;

  /// The API endpoint this operation targets.
  final String endpoint;

  /// The JSON-serializable payload for the operation.
  final Map<String, dynamic> payload;

  /// When the operation was originally queued.
  final DateTime timestamp;

  /// Number of times this operation has been attempted.
  final int attempts;

  /// Maximum number of retry attempts before the operation is discarded.
  static const int maxAttempts = 3;

  /// Whether this operation has exhausted its retry budget.
  bool get isExpired => attempts >= maxAttempts;

  /// Returns a copy with the attempt counter incremented by one.
  QueuedOperation incrementAttempts() {
    return QueuedOperation(
      id: id,
      type: type,
      endpoint: endpoint,
      payload: payload,
      timestamp: timestamp,
      attempts: attempts + 1,
    );
  }

  factory QueuedOperation.fromJson(Map<String, dynamic> json) {
    return QueuedOperation(
      id: json['id'] as String,
      type: json['type'] as String,
      endpoint: json['endpoint'] as String,
      payload: Map<String, dynamic>.from(json['payload'] as Map),
      timestamp: DateTime.parse(json['timestamp'] as String),
      attempts: json['attempts'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'type': type,
      'endpoint': endpoint,
      'payload': payload,
      'timestamp': timestamp.toIso8601String(),
      'attempts': attempts,
    };
  }

  @override
  String toString() =>
      'QueuedOperation(id: $id, type: $type, endpoint: $endpoint, '
      'attempts: $attempts)';
}

/// Callback signature for processing a single queued operation.
///
/// Implementations should throw on failure so the queue can track retries.
typedef OperationProcessor = Future<void> Function(QueuedOperation operation);

/// A persistent FIFO queue for write operations that could not be sent while
/// the device was offline.
///
/// Operations are serialized to a JSON file in the app's documents directory
/// so they survive app restarts. On reconnect, [processQueue] replays them
/// in order, retrying up to [QueuedOperation.maxAttempts] times per item.
class SyncQueue {
  SyncQueue();

  static const String _fileName = 'sync_queue.json';

  /// In-memory mirror of the persisted queue.
  final List<QueuedOperation> _queue = [];

  /// Whether the queue file has been loaded into memory.
  bool _initialized = false;

  /// Whether a [processQueue] call is currently in progress.
  bool _processing = false;

  // ── Public API ──────────────────────────────────────────────────────────

  /// Number of operations currently in the queue.
  int get length => _queue.length;

  /// Whether there are operations waiting to be processed.
  bool get hasPending => _queue.isNotEmpty;

  /// Read-only snapshot of the current queue contents.
  List<QueuedOperation> get operations => List.unmodifiable(_queue);

  /// Loads the queue from disk. Safe to call multiple times; subsequent
  /// calls are no-ops.
  Future<void> initialize() async {
    if (_initialized) return;

    try {
      final file = await _queueFile();
      if (await file.exists()) {
        final contents = await file.readAsString();
        if (contents.isNotEmpty) {
          final List<dynamic> decoded = jsonDecode(contents) as List<dynamic>;
          _queue.addAll(
            decoded
                .map((item) =>
                    QueuedOperation.fromJson(item as Map<String, dynamic>))
                .toList(),
          );
          developer.log(
            'Loaded ${_queue.length} queued operations from disk',
            name: 'sync_queue',
          );
        }
      }
    } on FormatException catch (e) {
      developer.log(
        'Corrupt sync queue file, starting fresh: $e',
        name: 'sync_queue',
        level: 900,
      );
      _queue.clear();
    } on FileSystemException catch (e) {
      developer.log(
        'Could not read sync queue file: $e',
        name: 'sync_queue',
        level: 900,
      );
    }

    _initialized = true;
  }

  /// Adds an operation to the end of the queue and persists to disk.
  Future<void> enqueue(QueuedOperation operation) async {
    await initialize();
    _queue.add(operation);
    await _persist();
    developer.log(
      'Enqueued operation: ${operation.id} (${operation.type} '
      '${operation.endpoint})',
      name: 'sync_queue',
    );
  }

  /// Removes a specific operation by [id] and persists the change.
  Future<void> remove(String id) async {
    await initialize();
    _queue.removeWhere((op) => op.id == id);
    await _persist();
  }

  /// Clears all operations from the queue and deletes the persisted file.
  Future<void> clear() async {
    _queue.clear();
    try {
      final file = await _queueFile();
      if (await file.exists()) {
        await file.delete();
      }
    } on FileSystemException catch (e) {
      developer.log(
        'Could not delete sync queue file: $e',
        name: 'sync_queue',
        level: 900,
      );
    }
  }

  /// Processes all queued operations in FIFO order using the provided
  /// [processor] callback.
  ///
  /// Each operation is attempted up to [QueuedOperation.maxAttempts] times.
  /// Successful operations are removed from the queue. Failed operations that
  /// have not exceeded max attempts remain for the next sync cycle.
  ///
  /// Returns the number of operations successfully processed.
  Future<int> processQueue(OperationProcessor processor) async {
    if (_processing) {
      developer.log(
        'Queue processing already in progress, skipping',
        name: 'sync_queue',
      );
      return 0;
    }

    await initialize();

    if (_queue.isEmpty) return 0;

    _processing = true;
    int successCount = 0;
    final List<String> completedIds = [];
    final List<QueuedOperation> updatedOps = [];

    developer.log(
      'Processing ${_queue.length} queued operations',
      name: 'sync_queue',
    );

    // Take a snapshot so mutations during iteration are safe.
    final snapshot = List<QueuedOperation>.from(_queue);

    for (final operation in snapshot) {
      final tracked = operation.incrementAttempts();

      try {
        await processor(tracked);
        completedIds.add(tracked.id);
        successCount++;
        developer.log(
          'Successfully processed: ${tracked.id}',
          name: 'sync_queue',
        );
      } on Exception catch (e) {
        developer.log(
          'Failed to process ${tracked.id} '
          '(attempt ${tracked.attempts}/${QueuedOperation.maxAttempts}): $e',
          name: 'sync_queue',
          level: 900,
        );

        if (tracked.isExpired) {
          developer.log(
            'Operation ${tracked.id} exceeded max attempts, discarding',
            name: 'sync_queue',
            level: 1000,
          );
          completedIds.add(tracked.id);
        } else {
          updatedOps.add(tracked);
        }
      }
    }

    // Remove completed/expired operations, update retry counts for the rest.
    _queue.removeWhere((op) => completedIds.contains(op.id));
    for (final updated in updatedOps) {
      final index = _queue.indexWhere((op) => op.id == updated.id);
      if (index >= 0) {
        _queue[index] = updated;
      }
    }

    await _persist();
    _processing = false;

    developer.log(
      'Queue processing complete: $successCount succeeded, '
      '${_queue.length} remaining',
      name: 'sync_queue',
    );

    return successCount;
  }

  // ── Persistence ─────────────────────────────────────────────────────────

  Future<File> _queueFile() async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/$_fileName');
  }

  Future<void> _persist() async {
    try {
      final file = await _queueFile();
      final encoded = jsonEncode(_queue.map((op) => op.toJson()).toList());
      await file.writeAsString(encoded, flush: true);
    } on FileSystemException catch (e) {
      developer.log(
        'Could not persist sync queue: $e',
        name: 'sync_queue',
        level: 900,
      );
    }
  }
}
