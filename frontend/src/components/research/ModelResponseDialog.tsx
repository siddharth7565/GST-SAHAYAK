import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ModelAnswerResult } from '../../types';
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter, DialogClose } from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Bot, Clock, CheckCircle2, Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface ModelResponseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: ModelAnswerResult | null;
}

export function ModelResponseDialog({ open, onOpenChange, result }: ModelResponseDialogProps) {
  const [copied, setCopied] = useState(false);

  if (!result) return null;

  const handleCopy = () => {
    if (result.answer) {
      navigator.clipboard.writeText(result.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogClose onClick={() => onOpenChange(false)} />
        <div className="flex items-center justify-between pr-8">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gst-orange-light border border-gst-orange/40 flex items-center justify-center text-gst-orange-deep font-bold shadow-2xs">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="uppercase tracking-tight">
                {result.provider} Answer
              </DialogTitle>
              <div className="text-xs font-mono text-gst-muted">
                Model: {result.model}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {result.response_time && (
              <Badge variant="outline" className="text-xs font-semibold text-gst-dark border-gst-border">
                <Clock className="h-3 w-3 mr-1 text-gst-orange-deep" />
                {result.response_time.toFixed(2)}s
              </Badge>
            )}
            <Badge variant="success" className="text-xs font-bold uppercase">
              <CheckCircle2 className="h-3 w-3 mr-1" /> SUCCESS
            </Badge>
          </div>
        </div>
      </DialogHeader>

      <DialogContent>
        <div className="prose-gst font-sans">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {result.answer || 'No answer text provided.'}
          </ReactMarkdown>
        </div>
      </DialogContent>

      <DialogFooter>
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopy}
          className="gap-1.5 text-xs font-semibold"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-gst-green" /> Copied to Clipboard
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy Full Answer
            </>
          )}
        </Button>

        <Button
          size="sm"
          onClick={() => onOpenChange(false)}
          className="bg-gst-orange hover:bg-gst-orange-hover text-gst-dark font-semibold text-xs"
        >
          Close
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
