import styles from "./repo.module.css";

export function RepoPermissionHint() {
  return (
    <p className={styles.permissionHint} role="note">
      <strong>建议只读最小权限：</strong>
      GitHub 细粒度 PAT 仅授予目标仓库 Contents: read 与 Metadata: read；云效令牌仅授予代码库读取。
      系统不发起任何写操作，也不克隆仓库、不建立代码索引。
    </p>
  );
}
