import clsx from "clsx";

export type LoadingVariant = "card" | "list" | "chat";

export interface LoadingStateProps {
  variant?: LoadingVariant;
  /** Number of skeleton items to show */
  count?: number;
  className?: string;
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "animate-pulse rounded-[8px] bg-[var(--color-gray-200)]",
        className,
      )}
    />
  );
}

function CardSkeleton() {
  return (
    <div className="rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5">
      <Skeleton className="h-5 w-2/3 mb-3" />
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-5/6 mb-2" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="flex items-center gap-3 py-3">
      <Skeleton className="h-10 w-10 rounded-full shrink-0" />
      <div className="flex-1">
        <Skeleton className="h-4 w-1/3 mb-2" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  );
}

function ChatSkeleton() {
  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[80%] rounded-[12px] bg-[var(--color-surface-card)] p-4 shadow-[var(--shadow-card)]">
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-5/6 mb-2" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}

const variantMap: Record<LoadingVariant, () => React.ReactNode> = {
  card: () => <CardSkeleton />,
  list: () => <ListSkeleton />,
  chat: () => <ChatSkeleton />,
};

export function LoadingState({
  variant = "card",
  count = 3,
  className,
}: LoadingStateProps) {
  const Renderer = variantMap[variant];

  return (
    <div
      role="status"
      aria-label="Loading"
      className={clsx("flex flex-col gap-4", className)}
    >
      {Array.from({ length: count }, (_, i) => (
        <div key={i}>{Renderer()}</div>
      ))}
      <span className="sr-only">Loading...</span>
    </div>
  );
}
