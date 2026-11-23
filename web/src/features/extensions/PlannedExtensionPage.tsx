import { Link, useParams } from "react-router";
import { Mascot } from "../../components/mascot/Mascot";
import { StatusPill } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/Feedback";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { findPlannedExtension } from "./catalog";
import styles from "./extensions.module.css";

const BACK_LINK = { to: "/", label: "返回首页" } as const;

export function PlannedExtensionPage() {
  const { key } = useParams();
  const extension = findPlannedExtension(key);

  if (!extension) {
    return (
      <PageContainer tier="md" className={styles.section}>
        <PageHeader
          backLink={BACK_LINK}
          title="平台扩展"
          description="请从左侧导航选择已规划的扩展能力。"
        />
        <ErrorState message="扩展能力不存在或尚未规划" retryable={false} />
      </PageContainer>
    );
  }

  return (
    <PageContainer tier="md" className={styles.section}>
      <PageHeader
        backLink={BACK_LINK}
        title={extension.name}
        description={extension.description}
        badge={<StatusPill status="planned" />}
      />
      <article className={styles.briefing}>
        <div className={styles.briefingHead}>
          <Mascot size={72} state="sleeping" label="鸮鸮" />
          <div className={styles.briefingCopy}>
            <span className={styles.eyebrow}>路线图占位 · {extension.capabilityId}</span>
            <strong>该能力已纳入平台路线图</strong>
            <p className={styles.meta}>计划落地：{extension.targetPhase}</p>
          </div>
        </div>

        <p className={styles.callout}>{extension.summary}</p>

        <div className={styles.roadmap}>
          {extension.workflowSteps.map((step) => (
            <span key={step} className={styles.roadmapStep}>
              {step}
            </span>
          ))}
        </div>

        <section className={styles.guardrails} aria-label="架构红线">
          <h2 className={styles.guardrailsTitle}>架构红线与约束</h2>
          <ul className={styles.guardrailList}>
            {extension.guardrails.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </section>

        <p className={styles.docNote}>规划文档：{extension.docRef}</p>

        <div className={styles.actions}>
          <Link to="/sessions" className={styles.jump}>
            前往分析会话
          </Link>
          <Link to="/knowledge-bases" className={styles.jump}>
            查看知识库
          </Link>
          <Link to="/providers" className={styles.jump}>
            管理 AI 提供商
          </Link>
        </div>
      </article>
    </PageContainer>
  );
}
