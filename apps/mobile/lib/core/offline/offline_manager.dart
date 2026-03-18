import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'sync_queue.dart';

// ── Connectivity Status ───────────────────────────────────────────────────

/// Represents the current network and sync state of the application.
enum OfflineStatus {
  /// Device has network connectivity and data is current.
  online,

  /// Device has no network connectivity; cached data is served.
  offline,

  /// Device is online and pending operations are being synced.
  syncing,
}

// ── Offline Manager ───────────────────────────────────────────────────────

/// Manages offline capabilities for the AITE mobile application.
///
/// Responsibilities:
/// - Detect connectivity changes using periodic DNS lookups (dart:io based,
///   no external package required).
/// - Cache conversations, reference tables, documents, and company profiles
///   for offline access.
/// - Queue write operations while offline via [SyncQueue].
/// - Replay queued operations when connectivity returns.
///
/// Consumers listen via [ChangeNotifier] to react to [status] changes.
class OfflineManager extends ChangeNotifier {
  OfflineManager({
    SyncQueue? syncQueue,
    this.connectivityCheckInterval = const Duration(seconds: 15),
    this.connectivityHost = 'dns.google',
  }) : syncQueue = syncQueue ?? SyncQueue();

  // ── Configuration ─────────────────────────────────────────────────────

  /// How often to probe network connectivity.
  final Duration connectivityCheckInterval;

  /// Host used for DNS-based connectivity probes.
  final String connectivityHost;

  // ── State ─────────────────────────────────────────────────────────────

  /// The queue of write operations waiting to be synced.
  final SyncQueue syncQueue;

  OfflineStatus _status = OfflineStatus.online;
  Timer? _connectivityTimer;
  bool _initialized = false;

  /// Current connectivity and sync status.
  OfflineStatus get status => _status;

  /// Convenience getter — true when the device is offline.
  bool get isOffline => _status == OfflineStatus.offline;

  /// Convenience getter — true when a sync is in progress.
  bool get isSyncing => _status == OfflineStatus.syncing;

  /// Number of operations waiting to be synced.
  int get pendingOperationCount => syncQueue.length;

  // ── SharedPreferences Keys ────────────────────────────────────────────

  static const String _conversationIdsKey = 'offline_conversation_ids';
  static const String _conversationPrefix = 'offline_conversation_';
  static const String _referenceTablePrefix = 'offline_ref_';
  static const String _companyProfilePrefix = 'offline_company_';
  static const String _lastSyncKey = 'offline_last_sync';

  // ── Lifecycle ─────────────────────────────────────────────────────────

  /// Initializes the offline manager: loads the sync queue, checks current
  /// connectivity, and starts the periodic connectivity monitor.
  ///
  /// Safe to call multiple times; subsequent calls are no-ops.
  Future<void> initialize() async {
    if (_initialized) return;

    await syncQueue.initialize();

    // Run an initial connectivity check synchronously.
    await _checkConnectivity();

    // Start periodic monitoring.
    _connectivityTimer = Timer.periodic(
      connectivityCheckInterval,
      (_) => _checkConnectivity(),
    );

    _initialized = true;
    developer.log(
      'OfflineManager initialized, status: ${_status.name}',
      name: 'offline',
    );
  }

  @override
  void dispose() {
    _connectivityTimer?.cancel();
    _connectivityTimer = null;
    super.dispose();
  }

  // ── Connectivity Detection ────────────────────────────────────────────

  /// Performs a DNS lookup to determine if the device has internet access.
  Future<void> _checkConnectivity() async {
    final bool wasOffline = _status == OfflineStatus.offline;
    final bool isOnline = await _hasInternetAccess();

    if (isOnline && wasOffline) {
      // Connectivity restored — sync pending operations.
      developer.log('Connectivity restored', name: 'offline');
      _updateStatus(OfflineStatus.syncing);
      await _syncPendingOperations();
      _updateStatus(OfflineStatus.online);
    } else if (!isOnline && _status != OfflineStatus.offline) {
      developer.log('Connectivity lost', name: 'offline');
      _updateStatus(OfflineStatus.offline);
    }
  }

  /// Attempts a DNS lookup to verify internet access.
  ///
  /// Returns `true` if the lookup succeeds, `false` otherwise.
  Future<bool> _hasInternetAccess() async {
    try {
      final result = await InternetAddress.lookup(connectivityHost)
          .timeout(const Duration(seconds: 5));
      return result.isNotEmpty && result.first.rawAddress.isNotEmpty;
    } on SocketException {
      return false;
    } on TimeoutException {
      return false;
    }
  }

  void _updateStatus(OfflineStatus newStatus) {
    if (_status != newStatus) {
      _status = newStatus;
      notifyListeners();
    }
  }

  /// Forces a manual connectivity check and sync attempt.
  ///
  /// Useful when the user explicitly requests a refresh.
  Future<void> forceConnectivityCheck() async {
    await _checkConnectivity();
  }

  // ── Conversation Caching ──────────────────────────────────────────────

  /// Caches a conversation (as a JSON-serializable map) for offline access.
  ///
  /// The conversation is stored in SharedPreferences keyed by
  /// [conversationId]. A separate index of cached conversation IDs is
  /// maintained for enumeration.
  Future<void> cacheConversation(
    int conversationId,
    Map<String, dynamic> conversationData,
  ) async {
    final prefs = await SharedPreferences.getInstance();

    // Store the conversation data.
    final key = '$_conversationPrefix$conversationId';
    await prefs.setString(key, jsonEncode(conversationData));

    // Update the index of cached conversation IDs.
    final ids = prefs.getStringList(_conversationIdsKey) ?? [];
    final idStr = conversationId.toString();
    if (!ids.contains(idStr)) {
      ids.add(idStr);
      await prefs.setStringList(_conversationIdsKey, ids);
    }

    developer.log(
      'Cached conversation $conversationId',
      name: 'offline',
    );
  }

  /// Retrieves a cached conversation by [conversationId].
  ///
  /// Returns `null` if the conversation has not been cached.
  Future<Map<String, dynamic>?> getCachedConversation(
    int conversationId,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_conversationPrefix$conversationId';
    final raw = prefs.getString(key);
    if (raw == null) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  /// Returns all cached conversations as a list of JSON maps.
  Future<List<Map<String, dynamic>>> getCachedConversations() async {
    final prefs = await SharedPreferences.getInstance();
    final ids = prefs.getStringList(_conversationIdsKey) ?? [];
    final List<Map<String, dynamic>> results = [];

    for (final idStr in ids) {
      final key = '$_conversationPrefix$idStr';
      final raw = prefs.getString(key);
      if (raw != null) {
        results.add(jsonDecode(raw) as Map<String, dynamic>);
      }
    }

    return results;
  }

  /// Removes a specific conversation from the cache.
  Future<void> removeCachedConversation(int conversationId) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_conversationPrefix$conversationId';
    await prefs.remove(key);

    final ids = prefs.getStringList(_conversationIdsKey) ?? [];
    ids.remove(conversationId.toString());
    await prefs.setStringList(_conversationIdsKey, ids);
  }

  // ── Reference Table Caching ───────────────────────────────────────────

  /// Caches a reference table (CPF rates, levy rates, leave entitlements,
  /// etc.) for offline access.
  ///
  /// [tableName] is a logical key like 'cpf_rates', 'levy_rates', or
  /// 'leave_entitlements'. The data is stored as a JSON-encoded string in
  /// SharedPreferences.
  Future<void> cacheReferenceTable(
    String tableName,
    Map<String, dynamic> tableData,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_referenceTablePrefix$tableName';
    await prefs.setString(key, jsonEncode(tableData));

    developer.log(
      'Cached reference table: $tableName',
      name: 'offline',
    );
  }

  /// Retrieves a cached reference table by [tableName].
  ///
  /// Returns `null` if the table has not been cached.
  Future<Map<String, dynamic>?> getCachedTable(String tableName) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_referenceTablePrefix$tableName';
    final raw = prefs.getString(key);
    if (raw == null) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  // ── Company Profile Caching ───────────────────────────────────────────

  /// Caches a company profile for offline access.
  Future<void> cacheCompanyProfile(
    int companyId,
    Map<String, dynamic> profileData,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_companyProfilePrefix$companyId';
    await prefs.setString(key, jsonEncode(profileData));

    developer.log(
      'Cached company profile: $companyId',
      name: 'offline',
    );
  }

  /// Retrieves a cached company profile by [companyId].
  ///
  /// Returns `null` if the profile has not been cached.
  Future<Map<String, dynamic>?> getCachedCompanyProfile(
    int companyId,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_companyProfilePrefix$companyId';
    final raw = prefs.getString(key);
    if (raw == null) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  // ── Document Caching (File System) ────────────────────────────────────

  /// Caches a document's binary content to the local file system.
  ///
  /// Documents are stored in an `offline_docs` subdirectory within the
  /// application documents directory. [documentId] is used as the filename.
  Future<void> cacheDocument(String documentId, List<int> bytes) async {
    final dir = await _documentsDir();
    final file = File('${dir.path}/$documentId');
    await file.writeAsBytes(bytes, flush: true);

    developer.log(
      'Cached document: $documentId (${bytes.length} bytes)',
      name: 'offline',
    );
  }

  /// Retrieves a cached document's binary content by [documentId].
  ///
  /// Returns `null` if the document has not been cached.
  Future<List<int>?> getCachedDocument(String documentId) async {
    final dir = await _documentsDir();
    final file = File('${dir.path}/$documentId');
    if (!await file.exists()) return null;
    return file.readAsBytes();
  }

  /// Removes a cached document by [documentId].
  Future<void> removeCachedDocument(String documentId) async {
    final dir = await _documentsDir();
    final file = File('${dir.path}/$documentId');
    if (await file.exists()) {
      await file.delete();
    }
  }

  /// Lists the IDs of all cached documents.
  Future<List<String>> getCachedDocumentIds() async {
    final dir = await _documentsDir();
    if (!await dir.exists()) return [];
    final entities = await dir.list().toList();
    return entities
        .whereType<File>()
        .map((f) => f.uri.pathSegments.last)
        .toList();
  }

  Future<Directory> _documentsDir() async {
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/offline_docs');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  // ── Operation Queueing ────────────────────────────────────────────────

  /// Queues a write operation for later execution.
  ///
  /// Use this when the device is offline and a user action would normally
  /// result in an API call. The [type] is typically an HTTP method
  /// ('POST', 'PUT', 'DELETE'), [endpoint] is the API path, and [payload]
  /// contains the request body.
  Future<void> queueOperation({
    required String type,
    required String endpoint,
    required Map<String, dynamic> payload,
  }) async {
    final operation = QueuedOperation(
      id: '${DateTime.now().millisecondsSinceEpoch}_'
          '${endpoint.hashCode.abs()}',
      type: type,
      endpoint: endpoint,
      payload: payload,
      timestamp: DateTime.now(),
    );

    await syncQueue.enqueue(operation);
    notifyListeners();

    developer.log(
      'Queued operation: ${operation.id} ($type $endpoint)',
      name: 'offline',
    );
  }

  // ── Sync Processing ──────────────────────────────────────────────────

  /// Processor callback for sending queued operations to the backend.
  ///
  /// Set this before calling [syncPendingOperations] or relying on
  /// automatic sync-on-reconnect. The callback receives a
  /// [QueuedOperation] and should throw on failure.
  OperationProcessor? operationProcessor;

  /// Processes all pending queued operations.
  ///
  /// Called automatically when connectivity is restored, but can also be
  /// triggered manually. Requires [operationProcessor] to be set.
  ///
  /// Returns the number of operations successfully processed.
  Future<int> syncPendingOperations() async {
    if (!syncQueue.hasPending) return 0;

    final processor = operationProcessor;
    if (processor == null) {
      developer.log(
        'No operation processor configured, cannot sync',
        name: 'offline',
        level: 900,
      );
      return 0;
    }

    _updateStatus(OfflineStatus.syncing);

    final count = await syncQueue.processQueue(processor);

    // Record the last successful sync time.
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastSyncKey, DateTime.now().toIso8601String());

    _updateStatus(
      syncQueue.hasPending ? OfflineStatus.online : OfflineStatus.online,
    );
    notifyListeners();

    return count;
  }

  /// Internal sync triggered by connectivity restoration.
  Future<void> _syncPendingOperations() async {
    await syncPendingOperations();
  }

  /// Returns the timestamp of the last successful sync, or `null` if no
  /// sync has ever completed.
  Future<DateTime?> get lastSyncTime async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_lastSyncKey);
    if (raw == null) return null;
    return DateTime.tryParse(raw);
  }

  // ── Cache Management ──────────────────────────────────────────────────

  /// Clears all offline caches: conversations, reference tables, company
  /// profiles, documents, and the sync queue.
  ///
  /// Useful when the user logs out or when storage reclamation is needed.
  Future<void> clearAllCaches() async {
    final prefs = await SharedPreferences.getInstance();

    // Clear conversations.
    final ids = prefs.getStringList(_conversationIdsKey) ?? [];
    for (final id in ids) {
      await prefs.remove('$_conversationPrefix$id');
    }
    await prefs.remove(_conversationIdsKey);

    // Clear reference tables and company profiles by iterating all keys.
    final allKeys = prefs.getKeys();
    for (final key in allKeys) {
      if (key.startsWith(_referenceTablePrefix) ||
          key.startsWith(_companyProfilePrefix)) {
        await prefs.remove(key);
      }
    }

    await prefs.remove(_lastSyncKey);

    // Clear cached documents from file system.
    final docDir = await _documentsDir();
    if (await docDir.exists()) {
      await docDir.delete(recursive: true);
    }

    // Clear sync queue.
    await syncQueue.clear();

    developer.log('All offline caches cleared', name: 'offline');
    notifyListeners();
  }

  /// Returns an approximate size in bytes of the offline caches.
  ///
  /// Includes cached documents on disk. SharedPreferences data is
  /// estimated from string lengths.
  Future<int> estimateCacheSize() async {
    int totalBytes = 0;

    // Estimate SharedPreferences data.
    final prefs = await SharedPreferences.getInstance();
    final allKeys = prefs.getKeys();
    for (final key in allKeys) {
      if (key.startsWith(_conversationPrefix) ||
          key.startsWith(_referenceTablePrefix) ||
          key.startsWith(_companyProfilePrefix)) {
        final value = prefs.getString(key);
        if (value != null) {
          totalBytes += value.length * 2; // Rough UTF-16 estimate.
        }
      }
    }

    // Measure document files on disk.
    final docDir = await _documentsDir();
    if (await docDir.exists()) {
      await for (final entity in docDir.list()) {
        if (entity is File) {
          totalBytes += await entity.length();
        }
      }
    }

    return totalBytes;
  }
}
