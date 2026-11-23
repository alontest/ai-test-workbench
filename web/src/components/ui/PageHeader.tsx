import type { ReactNode } from "react";
import { Link } from "react-router";
import styles from "./PageHeader.module.css";

type PageWidth = "xl" | "lg" | "md" | "sm";

const WIDTH_CLASS: Record<PageWidth, string> = {
  xl: styles.tierXl,
  lg: styles.tierLg,
  md: styles.tierMd,
  sm: styles.tierSm,
};

export interface PageHeaderProps {
  /** 页面主标题，渲染为唯一 <h1>。 */
  title: ReactNode;
  /** 一句话说明页面用途与边界。 */
  description?: ReactNode;
  /** 标题右侧的状态徽标。 */
  badge?: ReactNode;
  /** 可选的返回上级链接。 */
  backLink?: { to: string; label: string };
  /** 右上角主操作。 */
  actions?: ReactNode;
  className?: string;
}

/**
 * 页面标题区（四段节奏的第 ① 段）。
 * Loading / Error / Empty 期间调用方必须保持渲染，只替换内容区。
 */
export function PageHeader({
  title,
  description,
  badge,
  backLink,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header className={[styles.header, className].filter(Boolean).join(" ")}>
      {backLink ? (
        <Link className={styles.backLink} to={backLink.to}>
          <span aria-hidden="true">←</span>
          {backLink.label}
        </Link>
      ) : null}
      <div className={styles.titleRow}>
        <div className={styles.titleGroup}>
          <div className={styles.titleLine}>
            <h1 className={styles.title}>{title}</h1>
            {badge ? <span className={styles.badge}>{badge}</span> : null}
          </div>
          {description ? <p className={styles.description}>{description}</p> : null}
        </div>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </div>
    </header>
  );
}

export interface PageContainerProps {
  /** 内容宽度分级，默认全宽工作台。 */
  tier?: PageWidth;
  className?: string;
  children: ReactNode;
}

/** 按页面类型限宽的单栏容器，配合 AppShell 的内边距使用。 */
export function PageContainer({
  tier = "xl",
  className,
  children,
}: PageContainerProps) {
  return (
    <div className={[styles.container, WIDTH_CLASS[tier], className].filter(Boolean).join(" ")}>
      {children}
    </div>
  );
}
