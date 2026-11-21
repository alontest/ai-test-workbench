import type { RepoBindingSummary } from "../api/types";
import styles from "./browse.module.css";

export interface RevokedNoticeProps {
  binding: RepoBindingSummary;
}

export function RevokedNotice({ binding }: RevokedNoticeProps) {
  return (
    <p className={styles.bannerWarning} role="status" data-testid="revoked-notice">
      <strong>已解绑，目录树与文件读取不可用。</strong>{" "}
      仓库 / 分支 / 提交快照只读可查；历史会话、制品与调用记录未修改。
      重新绑定会生成新 bindingId。
      <span className={styles.muted}>（{binding.repoName}）</span>
    </p>
  );
}
