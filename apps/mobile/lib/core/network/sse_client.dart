import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

/// A single Server-Sent Event parsed from the stream.
class SSEEvent {
  const SSEEvent({
    required this.event,
    required this.data,
  });

  /// The event type (e.g. "start", "token", "complete").
  final String event;

  /// Parsed JSON payload for this event.
  final Map<String, dynamic> data;

  @override
  String toString() => 'SSEEvent(event: $event, data: $data)';
}

/// Client for consuming Server-Sent Events from the AITE backend.
///
/// Uses Dio's [ResponseType.stream] to receive a byte stream, then parses
/// the standard SSE wire format (`event: ...\ndata: ...\n\n`) into typed
/// [SSEEvent] objects.
///
/// Usage:
/// ```dart
/// final stream = sseClient.stream('/advisory/stream', {'query': '...'});
/// await for (final event in stream) {
///   if (event.event == 'token') { ... }
/// }
/// ```
class SSEClient {
  const SSEClient({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// Opens a POST SSE connection to [path] with the given [body] and
  /// returns a stream of parsed [SSEEvent] objects.
  ///
  /// The stream completes when the server closes the connection or when
  /// a "complete" event is received.
  Stream<SSEEvent> stream(
    String path,
    Map<String, dynamic> body,
  ) async* {
    final response = await _dio.post<ResponseBody>(
      path,
      data: body,
      options: Options(
        responseType: ResponseType.stream,
        headers: <String, dynamic>{
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
      ),
    );

    final byteStream = response.data!.stream;
    final stringStream = utf8.decoder.bind(byteStream);
    final lineStream = const LineSplitter().bind(stringStream);

    String? currentEvent;
    final dataBuffer = StringBuffer();

    await for (final line in lineStream) {
      if (line.startsWith('event:')) {
        currentEvent = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        dataBuffer.write(line.substring(5).trim());
      } else if (line.isEmpty) {
        // Empty line signals end of an event block.
        if (currentEvent != null && dataBuffer.isNotEmpty) {
          final rawData = dataBuffer.toString();
          Map<String, dynamic> parsedData;

          try {
            parsedData =
                json.decode(rawData) as Map<String, dynamic>;
          } catch (_) {
            // If the data isn't valid JSON, wrap it as a text payload.
            parsedData = <String, dynamic>{'text': rawData};
          }

          final eventType = currentEvent;
          yield SSEEvent(event: eventType, data: parsedData);

          // Stop after "complete" — the server is done.
          if (eventType == 'complete') {
            return;
          }
        }

        // Reset for the next event block.
        currentEvent = null;
        dataBuffer.clear();
      }
    }

    // Handle trailing event without a final blank line.
    if (currentEvent != null && dataBuffer.isNotEmpty) {
      final rawData = dataBuffer.toString();
      Map<String, dynamic> parsedData;

      try {
        parsedData = json.decode(rawData) as Map<String, dynamic>;
      } catch (_) {
        parsedData = <String, dynamic>{'text': rawData};
      }

      yield SSEEvent(event: currentEvent, data: parsedData);
    }
  }
}
