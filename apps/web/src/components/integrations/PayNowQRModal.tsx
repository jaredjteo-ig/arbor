"use client";

import { useEffect, useRef, useCallback } from "react";
import { X, Download, Clock, DollarSign } from "lucide-react";
import { AppButton, toast } from "@/components/design-system";
import { usePayNowQR } from "@/hooks/api";

/* ── Types ────────────────────────────────────────────────── */

export interface PayNowQRModalProps {
  /** Amount in SGD */
  amount: number;
  /** Payment reference (e.g. claim ID) */
  reference: string;
  /** Called when the modal should close */
  onClose: () => void;
}

/* ── QR Code Display ─────────────────────────────────────── */

function QRCodeDisplay({ qrData }: { qrData: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !qrData) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // If qr_data is a data URL (base64-encoded image)
    if (qrData.startsWith("data:image")) {
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
      };
      img.src = qrData;
      return;
    }

    // If qr_data is a raw SVG or other format, render as text placeholder
    canvas.width = 256;
    canvas.height = 256;
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, 256, 256);
    ctx.fillStyle = "#1E3A5F";
    ctx.font = "14px monospace";
    ctx.textAlign = "center";
    ctx.fillText("PayNow QR", 128, 128);
  }, [qrData]);

  return (
    <canvas
      ref={canvasRef}
      className="mx-auto rounded-[8px] border border-[var(--color-gray-200)]"
      style={{ width: 256, height: 256 }}
    />
  );
}

/* ── Modal ────────────────────────────────────────────────── */

export function PayNowQRModal({
  amount,
  reference,
  onClose,
}: PayNowQRModalProps) {
  const { mutate: generateQR, data, isPending, error } = usePayNowQR();

  // Generate QR code on mount
  useEffect(() => {
    generateQR({ amount, reference });
  }, [amount, reference, generateQR]);

  const formatCurrency = (amt: number) =>
    new Intl.NumberFormat("en-SG", {
      style: "currency",
      currency: "SGD",
    }).format(amt);

  const handleDownload = useCallback(() => {
    if (!data?.qr_data) return;

    try {
      // If it's a data URL, download directly
      const link = document.createElement("a");
      link.href = data.qr_data;
      link.download = `paynow-${reference}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("QR code downloaded.");
    } catch {
      toast.error("Could not download QR code.");
    }
  }, [data, reference]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="paynow-title"
        className="relative bg-[var(--color-surface-card)] rounded-[12px] shadow-[var(--shadow-modal)]
          border border-[var(--color-gray-200)] max-w-md w-full"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-gray-200)]">
          <h2
            id="paynow-title"
            className="text-lg font-semibold text-[var(--color-gray-900)]"
          >
            PayNow QR Code
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center justify-center rounded-lg p-2 min-h-[36px] min-w-[36px]
              text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)] transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            aria-label="Close"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Loading */}
          {isPending && (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="animate-pulse rounded-[8px] bg-[var(--color-gray-200)] w-64 h-64" />
              <p className="text-sm text-[var(--color-gray-500)]">
                Generating QR code...
              </p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="text-center py-6">
              <p className="text-sm text-[var(--color-error)]">
                Could not generate QR code. Please try again.
              </p>
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => generateQR({ amount, reference })}
                className="mt-3"
              >
                Retry
              </AppButton>
            </div>
          )}

          {/* QR Code */}
          {data && (
            <>
              <QRCodeDisplay qrData={data.qr_data} />

              {/* Payment details */}
              <div className="space-y-2 p-4 rounded-[8px] bg-[var(--color-gray-50)]">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-sm text-[var(--color-gray-500)]">
                    <DollarSign className="h-3.5 w-3.5" aria-hidden="true" />
                    Amount
                  </span>
                  <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                    {formatCurrency(data.amount)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-sm text-[var(--color-gray-500)]">
                    <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                    Reference
                  </span>
                  <span className="text-sm font-mono text-[var(--color-gray-900)]">
                    {data.reference}
                  </span>
                </div>
                {data.expires_at && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-[var(--color-gray-500)]">
                      Expires
                    </span>
                    <span className="text-sm text-[var(--color-gray-700)]">
                      {new Date(data.expires_at).toLocaleString("en-SG", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-[var(--color-gray-200)]">
          <AppButton variant="outlined" size="md" onClick={onClose}>
            Close
          </AppButton>
          {data && (
            <AppButton variant="primary" size="md" onClick={handleDownload}>
              <Download className="h-4 w-4" aria-hidden="true" />
              Download QR
            </AppButton>
          )}
        </div>
      </div>
    </div>
  );
}
