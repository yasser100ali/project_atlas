import type { Attachment } from "ai";

import { LoaderIcon } from "./icons";

export const PreviewAttachment = ({
  attachment,
  isUploading = false,
}: {
  attachment: Attachment;
  isUploading?: boolean;
}) => {
  const { name, url, contentType } = attachment;

  // Render PDFs as an embedded viewer; otherwise fall back to thumbnail/link styles
  if (contentType === "application/pdf") {
    return (
      <div className="flex flex-col gap-2 w-full">
        <div className="w-full rounded-md overflow-hidden">
          <iframe
            src={url}
            title={name || "PDF"}
            className="w-full h-[640px]"
          />
        </div>
        <div className="text-xs text-zinc-500">
          <a href={url} target="_blank" rel="noopener noreferrer" className="underline">Open</a>
          <span> · </span>
          <a href={url} download={name} className="underline">Download</a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="w-20 aspect-video bg-muted rounded-md relative flex flex-col items-center justify-center">
        {contentType ? (
          contentType.startsWith("image") ? (
            // NOTE: it is recommended to use next/image for images
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={url}
              src={url}
              alt={name ?? "An image attachment"}
              className="rounded-md size-full object-cover"
            />
          ) : (
            <div className="text-xs p-2">{name}</div>
          )
        ) : (
          <div className="" />
        )}

        {isUploading && (
          <div className="animate-spin absolute text-zinc-500">
            <LoaderIcon />
          </div>
        )}
      </div>
      <div className="text-xs text-zinc-500 max-w-16 truncate">{name}</div>
    </div>
  );
};
