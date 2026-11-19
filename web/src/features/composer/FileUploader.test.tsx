import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { FileUploader } from "./FileUploader";

const MAX_BYTES = 10 * 1024 * 1024;

function namedFile(name: string, content = "hello") {
  return new File([content], name, { type: "text/plain" });
}

function renderUploader(existingFileNames: string[] = []) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  const api = installFetchMock();
  return {
    user: userEvent.setup(),
    api,
    ...render(
      <QueryClientProvider client={client}>
        <FileUploader sessionId={42} existingFileNames={existingFileNames} />
      </QueryClientProvider>,
    ),
  };
}

describe("TC-036 上传三查拒绝可移除后重提", () => {
  test("TC-036 类型/大小/数量拒绝标红且不阻止移除后重提", async () => {
    const { user, api } = renderUploader();
    const input = screen.getByLabelText(/选择文件/);

    await user.upload(input, namedFile("malware.exe"));
    expect(screen.getByText(/不支持 \.exe/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /上传/ })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /移除/ }));
    expect(screen.queryByText(/不支持 \.exe/)).not.toBeInTheDocument();

    const oversized = namedFile("big.log");
    Object.defineProperty(oversized, "size", { value: MAX_BYTES + 1 });
    await user.upload(input, oversized);
    expect(screen.getByText(/超过 10MB/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /移除/ }));

    const tooMany = Array.from({ length: 11 }, (_, index) =>
      namedFile(`file-${index}.log`),
    );
    await user.upload(input, tooMany);
    expect(screen.getByText(/最多上传 10 个/)).toBeInTheDocument();
    expect(api.fetch).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /清空|移除全部/ }));
    await user.upload(input, namedFile("app.log"));
    api.on("POST", "/api/v1/sessions/42/artifacts", () =>
      jsonResponse(
        {
          items: [
            {
              artifactId: 9,
              sessionId: 42,
              kind: "upload",
              fileName: "app.log",
              mimeType: "text/plain",
              byteSize: 5,
              createdAt: "2026-11-18T02:04:00Z",
            },
          ],
          events: [
            {
              eventId: 8,
              type: "artifact",
              payload: { artifactId: 9, fileName: "app.log" },
            },
          ],
        },
        201,
      ),
    );
    await user.click(screen.getByRole("button", { name: /上传/ }));
    await waitFor(() => {
      expect(api.fetch).toHaveBeenCalled();
    });
  });
});

describe("TC-038 同名改名前提示", () => {
  test("TC-038 选择已存在文件名时提示将自动改名", async () => {
    const { user } = renderUploader(["app.log"]);
    await user.upload(screen.getByLabelText(/选择文件/), namedFile("app.log"));
    expect(screen.getByText(/将自动改名为 app-1\.log/)).toBeInTheDocument();
  });
});
