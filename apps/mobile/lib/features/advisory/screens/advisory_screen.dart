import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/models/advisory.dart';
import '../../../core/network/sse_client.dart';
import '../../../core/providers/api_providers.dart';
import '../../../core/providers/auth_providers.dart';

// ---------------------------------------------------------------------------
// Local chat message model
// ---------------------------------------------------------------------------

class _ChatMessage {
  _ChatMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.streaming = false,
  });

  final String role; // 'user' | 'assistant'
  String content;
  final DateTime timestamp;
  String? riskTier;
  double? confidenceScore;
  List<ProvisionCitation>? provisionsCited;
  bool streaming;
}

// ---------------------------------------------------------------------------
// Follow-up suggestion logic
// ---------------------------------------------------------------------------

List<String> _generateFollowUps(String? riskTier, String content) {
  if (riskTier == 'red') {
    return [
      'What are my immediate obligations?',
      'What documents do I need?',
      'What are the penalties?',
    ];
  }
  if (riskTier == 'amber') {
    return [
      'How do I fix this?',
      'What is the deadline?',
      'Generate the required document',
    ];
  }
  final lower = content.toLowerCase();
  if (lower.contains('cpf')) {
    return ['Calculate CPF for a specific employee', 'What about PR employees?'];
  }
  if (lower.contains('leave')) {
    return ['Calculate leave entitlement', 'What about part-time employees?'];
  }
  return ['Tell me more', 'What should I do next?'];
}

const _kInitialSuggestions = [
  'What leave entitlements do my employees have?',
  'How do I calculate CPF contributions?',
  'Am I compliant with the Employment Act?',
  'What are the foreign worker quota limits?',
  'How do I handle a resignation?',
];

// ---------------------------------------------------------------------------
// Main advisory screen
// ---------------------------------------------------------------------------

class AdvisoryScreen extends ConsumerStatefulWidget {
  const AdvisoryScreen({super.key, this.prefillQuestion});

  /// Optional question pre-filled from onboarding flow.
  final String? prefillQuestion;

  @override
  ConsumerState<AdvisoryScreen> createState() => _AdvisoryScreenState();
}

class _AdvisoryScreenState extends ConsumerState<AdvisoryScreen> {
  final List<_ChatMessage> _messages = [];
  final ScrollController _scrollCtl = ScrollController();
  bool _isStreaming = false;
  int? _conversationId;
  StreamSubscription<SSEEvent>? _streamSub;
  bool _prefillHandled = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.prefillQuestion != null &&
          widget.prefillQuestion!.isNotEmpty &&
          !_prefillHandled) {
        _prefillHandled = true;
        _sendMessage(widget.prefillQuestion!);
      }
    });
  }

  @override
  void dispose() {
    _streamSub?.cancel();
    _scrollCtl.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtl.hasClients) {
        _scrollCtl.animateTo(
          _scrollCtl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage(String text) async {
    if (_isStreaming || text.trim().isEmpty) return;

    HapticFeedback.lightImpact();

    // Add user message
    setState(() {
      _messages.add(_ChatMessage(
        role: 'user',
        content: text.trim(),
        timestamp: DateTime.now(),
      ));
      // Add placeholder assistant message
      _messages.add(_ChatMessage(
        role: 'assistant',
        content: '',
        timestamp: DateTime.now(),
        streaming: true,
      ));
      _isStreaming = true;
    });
    _scrollToBottom();

    // Get auth state for company_id
    final authState = ref.read(authStateProvider);
    int? companyId;
    if (authState is AuthAuthenticated) {
      companyId = authState.user.companyId;
    }

    // Start SSE stream
    final repo = ref.read(advisoryRepositoryProvider);
    try {
      final stream = repo.streamQuery(
        query: text.trim(),
        companyId: companyId,
        conversationId: _conversationId,
      );

      _streamSub = stream.listen(
        (event) {
          switch (event.event) {
            case 'start':
              final convId = event.data['conversation_id'] as int?;
              if (convId != null && _conversationId == null) {
                _conversationId = convId;
              }

            case 'token':
              final token = event.data['token'] as String? ?? '';
              setState(() {
                final last = _messages.last;
                last.content += token;
              });
              _scrollToBottom();

            case 'complete':
              final response = event.data['response'] as String? ?? '';
              final riskTier = event.data['risk_tier'] as String?;
              final confidence = event.data['confidence_score'] as num?;
              final provisionsRaw =
                  event.data['provisions_cited'] as List<dynamic>?;
              final provisions = provisionsRaw
                  ?.map((p) =>
                      ProvisionCitation.fromJson(p as Map<String, dynamic>))
                  .toList();

              final completeConvId = event.data['conversation_id'] as int?;
              if (completeConvId != null && _conversationId == null) {
                _conversationId = completeConvId;
              }

              setState(() {
                final last = _messages.last;
                last.content = response;
                last.riskTier = riskTier;
                last.confidenceScore = confidence?.toDouble();
                last.provisionsCited = provisions;
                last.streaming = false;
                _isStreaming = false;
              });
              _scrollToBottom();
              _streamSub = null;

            case 'error':
              final message =
                  event.data['message'] as String? ?? 'An error occurred';
              setState(() {
                final last = _messages.last;
                last.content = 'Sorry, something went wrong: $message';
                last.streaming = false;
                _isStreaming = false;
              });
              _streamSub = null;
          }
        },
        onError: (Object error) {
          setState(() {
            final last = _messages.last;
            last.content = 'Connection error. Please try again.';
            last.streaming = false;
            _isStreaming = false;
          });
          _streamSub = null;
        },
        onDone: () {
          // If stream ends without 'complete', mark done
          if (_isStreaming) {
            setState(() {
              final last = _messages.last;
              last.streaming = false;
              _isStreaming = false;
            });
          }
          _streamSub = null;
        },
      );
    } catch (e) {
      setState(() {
        final last = _messages.last;
        last.content = 'Failed to connect. Please check your connection.';
        last.streaming = false;
        _isStreaming = false;
      });
    }
  }

  void _handleFeedback(bool isPositive, String? text) {
    // TODO: Send feedback to backend
  }

  @override
  Widget build(BuildContext context) {
    final isEmpty = _messages.isEmpty;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Advisory'),
        actions: [
          IconButton(
            onPressed: () {
              // TODO: Conversation history drawer
            },
            icon: const Icon(Icons.history),
            tooltip: 'History',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Messages area
            Expanded(
              child: isEmpty
                  ? _EmptyState(
                      onSuggestionTap: _sendMessage,
                    )
                  : ListView.separated(
                      controller: _scrollCtl,
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.base,
                        vertical: AppSpacing.base,
                      ),
                      itemCount: _messages.length,
                      separatorBuilder: (_, _) =>
                          const SizedBox(height: AppSpacing.md),
                      itemBuilder: (context, index) {
                        final msg = _messages[index];
                        if (msg.role == 'user') {
                          return ChatBubble(
                            message: msg.content,
                            variant: ChatBubbleVariant.user,
                          );
                        }

                        // Assistant message
                        if (msg.streaming && msg.content.isEmpty) {
                          return const Align(
                            alignment: Alignment.centerLeft,
                            child: Padding(
                              padding: EdgeInsets.all(AppSpacing.md),
                              child: LoadingState(),
                            ),
                          );
                        }

                        return _SystemMessageWidget(
                          message: msg,
                          isLast: index == _messages.length - 1,
                          onSuggestionTap: _sendMessage,
                          onFeedback: _handleFeedback,
                        );
                      },
                    ),
            ),

            // Input area
            Container(
              decoration: BoxDecoration(
                color: AppColors.neutralWhite,
                border: Border(
                  top: BorderSide(color: AppColors.neutralGray200),
                ),
              ),
              child: ChatInput(
                onSend: _sendMessage,
                onVoicePressed: () {
                  /* Voice input placeholder */
                },
                hintText: _isStreaming
                    ? 'Waiting for response...'
                    : 'Ask an HR question...',
                enabled: !_isStreaming,
                suggestions:
                    isEmpty ? _kInitialSuggestions : null,
                onSuggestionSelected: _sendMessage,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty state widget
// ---------------------------------------------------------------------------

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onSuggestionTap});

  final ValueChanged<String> onSuggestionTap;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppColors.primaryNavy.withValues(alpha: 0.1),
                borderRadius: AppRadius.lg,
              ),
              child: const Icon(
                Icons.chat_bubble_outline,
                size: 32,
                color: AppColors.primaryNavy,
              ),
            ),
            const SizedBox(height: AppSpacing.base),
            Text(
              'Ask Central anything about HR compliance',
              style: AppTypography.title.copyWith(
                color: AppColors.neutralGray900,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Get instant, cited answers about employment law, CPF, '
              'foreign worker rules, leave entitlements, and more.',
              style: AppTypography.body.copyWith(
                color: AppColors.neutralGray500,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// System (assistant) message widget with risk tier, citations, feedback
// ---------------------------------------------------------------------------

class _SystemMessageWidget extends StatelessWidget {
  const _SystemMessageWidget({
    required this.message,
    required this.isLast,
    required this.onSuggestionTap,
    required this.onFeedback,
  });

  final _ChatMessage message;
  final bool isLast;
  final ValueChanged<String> onSuggestionTap;
  final void Function(bool isPositive, String? text) onFeedback;

  ChatBubbleRiskTier? get _bubbleRiskTier {
    return switch (message.riskTier) {
      'green' => ChatBubbleRiskTier.green,
      'amber' => ChatBubbleRiskTier.amber,
      'red' => ChatBubbleRiskTier.red,
      _ => null,
    };
  }

  RiskTier? get _badgeRiskTier {
    return switch (message.riskTier) {
      'green' => RiskTier.green,
      'amber' => RiskTier.amber,
      'red' => RiskTier.red,
      _ => null,
    };
  }

  AuthorityLevel _mapAuthority(ProvisionCitation citation) {
    // Use act name as a rough authority heuristic
    final act = citation.actName?.toLowerCase() ?? '';
    if (act.contains('act') || act.contains('statute')) {
      return AuthorityLevel.statutory;
    }
    if (act.contains('guideline') || act.contains('tripartite')) {
      return AuthorityLevel.guideline;
    }
    return AuthorityLevel.bestPractice;
  }

  @override
  Widget build(BuildContext context) {
    final isRed = message.riskTier == 'red';
    final citations = message.provisionsCited;
    final followUps = isLast && !message.streaming
        ? _generateFollowUps(message.riskTier, message.content)
        : <String>[];

    Widget? sourcesWidget;
    if (citations != null && citations.isNotEmpty) {
      sourcesWidget = Wrap(
        spacing: AppSpacing.xs,
        runSpacing: AppSpacing.xs,
        children: citations
            .map((c) => SourceCitation(
                  label: c.title,
                  authorityLevel: _mapAuthority(c),
                ))
            .toList(),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Risk tier header for RED responses
        if (isRed && !message.streaming)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: Row(
              children: [
                const Icon(Icons.warning, color: AppColors.riskRed, size: 20),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  'Action Required',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.riskRed,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

        // Main chat bubble
        ChatBubble(
          message: message.content,
          variant: ChatBubbleVariant.system,
          riskTier: _bubbleRiskTier,
          sources: sourcesWidget,
        ),

        // Streaming cursor
        if (message.streaming && message.content.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(left: AppSpacing.md, top: 2),
            child: SizedBox(
              width: 8,
              height: 16,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: AppColors.primaryNavy,
                  borderRadius: AppRadius.sm,
                ),
              ),
            ),
          ),

        // Risk tier badge (non-red, non-streaming)
        if (_badgeRiskTier != null && !isRed && !message.streaming) ...[
          const SizedBox(height: AppSpacing.xs),
          Row(
            children: [
              RiskTierBadge(tier: _badgeRiskTier!),
              if (message.confidenceScore != null) ...[
                const SizedBox(width: AppSpacing.sm),
                Text(
                  'Confidence: ${(message.confidenceScore! * 100).round()}%',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray400,
                  ),
                ),
              ],
            ],
          ),
        ],

        // RED: Connect to specialist CTA
        if (isRed && !message.streaming) ...[
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            width: double.infinity,
            child: AppButton(
              label: 'Connect to Employment Law Specialist',
              onPressed: () {
                /* Connect to specialist flow */
              },
              variant: AppButtonVariant.outlined,
              icon: Icons.phone,
              fullWidth: true,
            ),
          ),
        ],

        // Follow-up suggestions
        if (followUps.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: followUps
                .map((s) => ActionChip(
                      label: Text(
                        s,
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.primaryNavy,
                        ),
                      ),
                      backgroundColor: AppColors.neutralGray100,
                      side: const BorderSide(color: AppColors.neutralGray200),
                      shape: RoundedRectangleBorder(
                          borderRadius: AppRadius.full),
                      onPressed: () => onSuggestionTap(s),
                    ))
                .toList(),
          ),
        ],

        // Feedback buttons
        if (!message.streaming && isLast) ...[
          const SizedBox(height: AppSpacing.sm),
          FeedbackButtons(onFeedback: onFeedback),
        ],
      ],
    );
  }
}
