"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import clsx from "clsx";
import {
  MessageSquare,
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Pencil,
  Trash2,
  X,
  Check,
  Loader2,
} from "lucide-react";

export interface ConversationSummary {
  id: number;
  title: string;
  lastMessage: string;
  timestamp: string;
  riskTier?: string;
}

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNewConversation: () => void;
  onDelete?: (id: number) => void;
  onRename?: (id: number, title: string) => void;
  deleteLoading?: boolean;
  renameLoading?: boolean;
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
}

function groupByDate(conversations: ConversationSummary[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const groups: { label: string; items: ConversationSummary[] }[] = [
    { label: "Today", items: [] },
    { label: "This Week", items: [] },
    { label: "This Month", items: [] },
    { label: "Earlier", items: [] },
  ];

  for (const c of conversations) {
    const ts = new Date(c.timestamp);
    if (ts >= today) {
      groups[0].items.push(c);
    } else if (ts >= weekAgo) {
      groups[1].items.push(c);
    } else if (ts >= monthAgo) {
      groups[2].items.push(c);
    } else {
      groups[3].items.push(c);
    }
  }

  return groups.filter((g) => g.items.length > 0);
}

/* ── Three-dot menu for a single conversation ─────────────── */

interface ConversationMenuProps {
  conversationId: number;
  currentTitle: string;
  onRename: (id: number, title: string) => void;
  onDelete: (id: number) => void;
  deleteLoading: boolean;
  renameLoading: boolean;
}

function ConversationMenu({
  conversationId,
  currentTitle,
  onRename,
  onDelete,
  deleteLoading,
  renameLoading,
}: ConversationMenuProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editValue, setEditValue] = useState(currentTitle);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
        setConfirmDelete(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  // Focus input when entering edit mode
  useEffect(() => {
    if (editMode && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editMode]);

  const handleRenameSubmit = useCallback(() => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== currentTitle) {
      onRename(conversationId, trimmed);
    }
    setEditMode(false);
    setMenuOpen(false);
  }, [editValue, currentTitle, conversationId, onRename]);

  const handleRenameKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleRenameSubmit();
      } else if (e.key === "Escape") {
        setEditMode(false);
        setEditValue(currentTitle);
      }
    },
    [handleRenameSubmit, currentTitle],
  );

  const handleDeleteConfirm = useCallback(() => {
    onDelete(conversationId);
    setConfirmDelete(false);
    setMenuOpen(false);
  }, [conversationId, onDelete]);

  if (editMode) {
    return (
      <div
        className="flex items-center gap-1 flex-1 min-w-0"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleRenameKeyDown}
          onBlur={handleRenameSubmit}
          disabled={renameLoading}
          className="flex-1 min-w-0 text-sm bg-[var(--color-surface-input)] border border-[var(--color-gray-300)] rounded px-1.5 py-0.5 text-[var(--color-gray-900)] outline-none focus:border-[var(--color-primary)]"
          maxLength={200}
        />
        <button
          type="button"
          onClick={handleRenameSubmit}
          disabled={renameLoading}
          className="p-0.5 rounded hover:bg-[var(--color-gray-200)] text-[var(--color-success)]"
          aria-label="Confirm rename"
        >
          {renameLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Check className="h-3.5 w-3.5" />
          )}
        </button>
        <button
          type="button"
          onClick={() => {
            setEditMode(false);
            setEditValue(currentTitle);
          }}
          className="p-0.5 rounded hover:bg-[var(--color-gray-200)] text-[var(--color-gray-500)]"
          aria-label="Cancel rename"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen(!menuOpen);
          setConfirmDelete(false);
        }}
        className="p-1 rounded hover:bg-[var(--color-gray-200)] text-[var(--color-gray-400)] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
        aria-label="Conversation options"
      >
        <MoreHorizontal className="h-3.5 w-3.5" />
      </button>

      {menuOpen && (
        <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-dropdown)] py-1">
          {confirmDelete ? (
            <div className="px-3 py-2">
              <p className="text-xs text-[var(--color-gray-700)] mb-2">
                Delete this conversation?
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConfirm();
                  }}
                  disabled={deleteLoading}
                  className="flex-1 text-xs px-2 py-1 rounded bg-[var(--color-error)] text-white hover:opacity-90 disabled:opacity-50"
                >
                  {deleteLoading ? "..." : "Delete"}
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmDelete(false);
                  }}
                  className="flex-1 text-xs px-2 py-1 rounded border border-[var(--color-gray-300)] text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)]"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setEditMode(true);
                  setEditValue(currentTitle);
                  setMenuOpen(false);
                }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)] text-left"
              >
                <Pencil className="h-3.5 w-3.5" />
                Rename
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDelete(true);
                }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-gray-100)] text-left"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Sidebar Component ────────────────────────────────────── */

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNewConversation,
  onDelete,
  onRename,
  deleteLoading = false,
  renameLoading = false,
  collapsed,
  onToggle,
  className,
}: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = searchQuery.trim()
    ? conversations.filter(
        (c) =>
          c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          c.lastMessage.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : conversations;

  const groups = groupByDate(filtered);

  if (collapsed) {
    return (
      <div
        className={clsx(
          "flex flex-col items-center py-3 border-r border-[var(--color-gray-200)] bg-[var(--color-surface-card)]",
          className,
        )}
      >
        <button
          type="button"
          onClick={onToggle}
          aria-label="Expand conversation history"
          className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-gray-500)] min-w-[44px] min-h-[44px] flex items-center justify-center"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={onNewConversation}
          aria-label="New conversation"
          className="mt-2 p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-primary)] min-w-[44px] min-h-[44px] flex items-center justify-center"
        >
          <Plus className="h-5 w-5" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        "flex flex-col w-72 border-r border-[var(--color-gray-200)] bg-[var(--color-surface-card)]",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-[var(--color-gray-200)]">
        <h2 className="text-sm font-semibold text-[var(--color-gray-900)]">
          History
        </h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onNewConversation}
            aria-label="New conversation"
            className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-primary)] min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onToggle}
            aria-label="Collapse sidebar"
            className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-gray-500)] min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="p-2">
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-surface-input)] px-2 py-1.5">
          <Search className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="flex-1 bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--color-gray-400)] outline-none"
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {groups.length === 0 && (
          <div className="p-4 text-center text-sm text-[var(--color-gray-400)]">
            {searchQuery ? "No matching conversations" : "No conversations yet"}
          </div>
        )}

        {groups.map((group) => (
          <div key={group.label}>
            <div className="px-3 py-1.5 text-xs font-medium text-[var(--color-gray-400)] uppercase tracking-wider">
              {group.label}
            </div>
            {group.items.map((conv) => (
              <div
                key={conv.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(conv.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(conv.id);
                  }
                }}
                className={clsx(
                  "group w-full text-left px-3 py-2.5 transition-colors cursor-pointer",
                  "hover:bg-[var(--color-gray-100)]",
                  "focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-primary)]",
                  activeId === conv.id &&
                    "bg-[var(--color-primary-bg)] border-l-2 border-l-[var(--color-primary)]",
                )}
              >
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5 text-[var(--color-gray-400)] shrink-0" />
                  <span className="text-sm font-medium text-[var(--color-gray-900)] truncate flex-1 min-w-0">
                    {conv.title}
                  </span>
                  {onDelete && onRename && (
                    <ConversationMenu
                      conversationId={conv.id}
                      currentTitle={conv.title}
                      onRename={onRename}
                      onDelete={onDelete}
                      deleteLoading={deleteLoading}
                      renameLoading={renameLoading}
                    />
                  )}
                </div>
                <p className="mt-0.5 text-xs text-[var(--color-gray-500)] truncate pl-5">
                  {conv.lastMessage}
                </p>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
