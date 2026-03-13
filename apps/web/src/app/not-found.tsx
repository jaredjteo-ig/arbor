import { EmptyState } from "@/components/design-system";
import { FileQuestion } from "lucide-react";
import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <EmptyState
        icon={
          <FileQuestion
            className="h-12 w-12 text-[var(--color-gray-400)]"
            aria-hidden="true"
          />
        }
        message="Page not found"
        description="The page you are looking for does not exist or has been moved."
        action={
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 rounded-[8px] font-medium px-4 py-2 text-base min-h-[44px] bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-light)] active:bg-[var(--color-primary-dark)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
          >
            Go to Dashboard
          </Link>
        }
      />
    </div>
  );
}
