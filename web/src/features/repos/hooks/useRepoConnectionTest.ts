import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  testSavedConnection,
  testUnsavedConnection,
} from "../api/client";
import { repoKeys } from "../api/keys";
import type {
  RepoConnectionTestInput,
  RepoConnectionTestResponse,
} from "../api/types";

export interface RepoConnectionTestVariables {
  bindingId?: string;
  input?: RepoConnectionTestInput;
}

/**
 * 已保存测试会更新绑定状态；未保存测试不落库，也不写任何前端持久化。
 * 未保存结果只存在于调用方的组件 state 中。
 */
export function useTestRepoConnection() {
  const queryClient = useQueryClient();
  return useMutation<
    RepoConnectionTestResponse,
    Error,
    RepoConnectionTestVariables
  >({
    mutationFn: (variables) => {
      if (variables.bindingId) {
        return testSavedConnection(variables.bindingId);
      }
      if (!variables.input) {
        throw new Error("缺少测试连接参数");
      }
      return testUnsavedConnection(variables.input);
    },
    onSuccess: (_result, variables) => {
      if (variables.bindingId) {
        void queryClient.invalidateQueries({
          queryKey: repoKeys.binding(variables.bindingId),
        });
        void queryClient.invalidateQueries({ queryKey: ["repo", "bindings"] });
      }
    },
  });
}
