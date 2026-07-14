import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildAuthHeaders,
  mergePolledDocument,
  optimisticRemove,
  rollbackRemove,
  uploadDocumentWithProgress,
  validateUploadFile,
} from "../src/lib/documentsCore.js";

const limits = {
  max_size_mb: 1,
  max_pages: 300,
  allowed_mime_types: ["application/pdf"],
};

test("/documents page contains dropzone and empty state copy", async () => {
  const source = await readFile(new URL("../src/app/documents/page.tsx", import.meta.url), "utf8");
  assert.match(source, /documents-dropzone/);
  assert.match(source, /No documents uploaded/);
});

test("upload limits drive MIME and size validation before network", () => {
  const wrongMime = { type: "text/plain", size: 1 };
  const oversized = { type: "application/pdf", size: 2 * 1024 * 1024 };
  assert.deepEqual(validateUploadFile(wrongMime, limits), {
    ok: false,
    reason: "Only PDF files can be uploaded.",
  });
  assert.deepEqual(validateUploadFile(oversized, limits), {
    ok: false,
    reason: "File exceeds 1 MB.",
  });
});

test("auth header helper includes bearer token when present", () => {
  assert.deepEqual(buildAuthHeaders(() => "abc123"), { Authorization: "Bearer abc123" });
  assert.deepEqual(buildAuthHeaders(() => null), {});
});

test("upload progress indicator receives XHR progress events", async () => {
  const progress = [];
  class FakeXHR {
    upload = {};
    status = 202;
    responseText = JSON.stringify({ id: "1", status: "processing" });
    open() {}
    setRequestHeader() {}
    send() {
      this.upload.onprogress({ lengthComputable: true, loaded: 50, total: 100 });
      this.onload();
    }
  }
  const result = await uploadDocumentWithProgress(
    new Blob(["%PDF"], { type: "application/pdf" }),
    (value) => progress.push(value),
    () => new FakeXHR(),
  );
  assert.deepEqual(progress, [50]);
  assert.equal(result.status, "processing");
});

test("processing row transitions to indexed through polling merge", () => {
  const documents = [{ id: "1", filename: "a.pdf", status: "processing" }];
  const updated = { id: "1", filename: "a.pdf", status: "indexed" };
  assert.deepEqual(mergePolledDocument(documents, updated), [updated]);
});

test("failed status remains visible through polling merge", () => {
  const documents = [{ id: "1", filename: "a.pdf", status: "processing" }];
  const updated = { id: "1", filename: "a.pdf", status: "failed" };
  assert.equal(mergePolledDocument(documents, updated)[0].status, "failed");
});

test("delete removes optimistically and rolls back on failure", () => {
  const removed = { id: "1", filename: "a.pdf", uploaded_at: "2026-01-01T00:00:00Z" };
  const remaining = [{ id: "2", filename: "b.pdf", uploaded_at: "2026-01-02T00:00:00Z" }];
  assert.deepEqual(optimisticRemove([removed, ...remaining], "1"), remaining);
  assert.deepEqual(rollbackRemove(remaining, removed).map((row) => row.id), ["2", "1"]);
});
