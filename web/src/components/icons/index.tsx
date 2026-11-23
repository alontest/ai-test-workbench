/**
 * 图标层。两个来源，两套规则：
 *
 * 1. 功能图标（Feature*）—— 自绘，统一 24×24 网格、1.75 描边、圆头圆角、
 *    继承 currentColor。见 `web/src/styles/DESIGN.md` 的「图标」一节。
 * 2. 品牌标记（BrandGithub / BrandYunxiao）—— 使用品牌的原始形态与配色，
 *    不改描边、不重绘。品牌标志被改写就会失去识别度，那比风格统一更重要。
 */
import type { SVGProps } from "react";

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, "children"> {
  /** 渲染尺寸，默认 24。 */
  size?: number;
}

const FEATURE_STROKE = 1.75;

function FeatureSvg({
  size = 24,
  children,
  ...rest
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={FEATURE_STROKE}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

/* ─────────────────────────── 导航 / 入口 ─────────────────────────── */

/** 用例库：一叠用例卡，最上面一张有对勾。 */
export function FeatureCaseLibrary(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <rect x="3" y="7" width="14" height="13" rx="2" />
      <path d="M7 7V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-2" />
      <path d="M6.5 13.5 8.5 15.5 12 12" />
    </FeatureSvg>
  );
}

/** 分析 bug：放大镜里一条虫。 */
export function FeatureBugAnalysis(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 4 4" />
      <path d="M10.5 8v5M8 10.5h5" />
    </FeatureSvg>
  );
}

/** 排查日志：终端窗口里的几行。 */
export function FeatureLogTriage(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M7 9l2.5 2.5L7 14" />
      <path d="M12 14h5" />
    </FeatureSvg>
  );
}

/** 分析 SQL：数据库柱体。 */
export function FeatureSqlAnalysis(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <ellipse cx="12" cy="6" rx="8" ry="3" />
      <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" />
      <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
    </FeatureSvg>
  );
}

/** 生成回归清单：带序号勾选的清单。 */
export function FeatureRegressionList(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M9 6h11M9 12h11M9 18h11" />
      <path d="M4 5.5 5.5 7 7.5 4.5" />
      <path d="M4 11.5 5.5 13 7.5 10.5" />
      <circle cx="5.5" cy="18" r="1.5" />
    </FeatureSvg>
  );
}

/** 生成测试报告：文档 + 柱状图。 */
export function FeatureTestReport(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M6 2h8l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" />
      <path d="M14 2v5h5" />
      <path d="M8 17v-3M11.5 17v-5M15 17v-2" />
    </FeatureSvg>
  );
}

/* ─────────────────────────── 基座管理 ─────────────────────────── */

/** 项目上下文：分层结构。 */
export function FeatureProject(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M12 3 3 7.5 12 12l9-4.5L12 3Z" />
      <path d="m3 12.5 9 4.5 9-4.5" />
      <path d="m3 17 9 4.5 9-4.5" />
    </FeatureSvg>
  );
}

/** AI 提供商与模型：芯片。 */
export function FeatureProvider(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <path d="M9.5 9.5h5v5h-5z" />
      <path d="M10 3v3M14 3v3M10 18v3M14 18v3M3 10h3M3 14h3M18 10h3M18 14h3" />
    </FeatureSvg>
  );
}

/** 调用记录：带时间戳的列表。 */
export function FeatureCalls(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5V12l3 2" />
    </FeatureSvg>
  );
}

/** 知识库：翻开的书（中缝 + 两页，页角上翘）；书架线区分「库」。 */
export function FeatureKnowledge(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M12 6.5C10.4 5.2 8.4 4.6 6 4.6c-.6 0-1 .4-1 1v11.2c0 .6.4 1 1 1 2.4 0 4.4.6 6 1.9" />
      <path d="M12 6.5c1.6-1.3 3.6-1.9 6-1.9.6 0 1 .4 1 1v11.2c0 .6-.4 1-1 1-2.4 0-4.4.6-6 1.9" />
      <path d="M12 6.5v12.2" />
    </FeatureSvg>
  );
}

/** 仓库浏览：分支。 */
export function FeatureRepo(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <circle cx="6.5" cy="5" r="2.5" />
      <circle cx="6.5" cy="19" r="2.5" />
      <circle cx="17.5" cy="8" r="2.5" />
      <path d="M6.5 7.5v9" />
      <path d="M17.5 10.5c0 3-2.5 4.5-5.5 5" />
    </FeatureSvg>
  );
}

/** 会话（首页导航用）。 */
export function FeatureSession(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M20 15a2 2 0 0 1-2 2H8l-4 3V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10Z" />
      <path d="M8 8h8M8 11.5h5" />
    </FeatureSvg>
  );
}

/** 首页。 */
export function FeatureHome(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M3.5 10.5 12 3.5l8.5 7" />
      <path d="M5.5 9.5V19a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5V9.5" />
      <path d="M10 20.5v-6h4v6" />
    </FeatureSvg>
  );
}

/* ─────────────────────────── 平台扩展（规划中） ─────────────────────────── */

/** QA 技能库：带星芒标的方法论手册。 */
export function FeatureSkill(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <rect x="4" y="3.5" width="16" height="17" rx="2" />
      <path d="M8 8.5h8M8 12.5h5" />
      <path d="M15.5 14v4M13.5 16h4" />
    </FeatureSvg>
  );
}

/** MCP 工具源：插头与协议节点。 */
export function FeatureMcp(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <circle cx="5.5" cy="12" r="2.5" />
      <circle cx="18.5" cy="6.5" r="2.5" />
      <circle cx="18.5" cy="17.5" r="2.5" />
      <path d="M8 11l8-3.5M8 13l8 3.5" />
    </FeatureSvg>
  );
}

/** 审批中心：带对勾的盾牌。 */
export function FeatureApproval(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M12 3 5 6v5.5c0 4.4 3 8 7 9.5 4-1.5 7-5.1 7-9.5V6l-7-3Z" />
      <path d="m9 12 2 2 4-4" />
    </FeatureSvg>
  );
}

/** 变更审计：逆时针回溯与时间轴。 */
export function FeatureHistory(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3L4.5 9" />
      <path d="M4.5 4.5V9H9" />
      <path d="M12 8.5V12l2.5 1.5" />
    </FeatureSvg>
  );
}

/* ─────────────────────── 通用功能图标 ─────────────────────── */

export function IconCheck(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="m4.5 12.5 5 5 10-11" />
    </FeatureSvg>
  );
}
export function IconChevronRight(props: IconProps) {
  return (
    <FeatureSvg {...props}>
      <path d="m9 5 7 7-7 7" />
    </FeatureSvg>
  );
}
/* ─────────────────────────── 品牌标记 ─────────────────────────── */

/**
 * GitHub 官方 mark。用官方 path，24×24，currentColor 填充。
 * 不改描边、不重绘——品牌标志被改写会失去识别度。
 */
function BrandGithub({ size = 24, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="currentColor"
      aria-hidden="true"
      {...rest}
    >
      <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.21.09 1.85 1.24 1.85 1.24 1.07 1.84 2.81 1.31 3.5 1 .11-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.96 0-1.32.47-2.4 1.24-3.24-.13-.3-.54-1.53.12-3.18 0 0 1.01-.32 3.3 1.24a11.5 11.5 0 0 1 6 0c2.29-1.56 3.3-1.24 3.3-1.24.66 1.65.25 2.88.12 3.18.77.84 1.24 1.92 1.24 3.24 0 4.63-2.81 5.66-5.49 5.95.43.37.81 1.1.81 2.22v3.29c0 .32.21.7.83.58A12.02 12.02 0 0 0 24 12.5C24 5.87 18.63.5 12 .5Z" />
    </svg>
  );
}

/**
 * 云效标记。云效没有公开的品牌 mark，这里按它的品牌属性自绘：
 * 云效（Alibaba Cloud DevOps）主色为橙 #FF6A00，形态取「云 + 流水线」的抽象。
 * 明确标注为自绘，未来官方出 mark 时可直接替换此实现。
 */
function BrandYunxiao({ size = 24, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      aria-hidden="true"
      {...rest}
    >
      {/* 云：三段圆弧拼合的轮廓，比单个圆更像「云」 */}
      <path
        d="M7.6 18.2h9.1a4 4 0 0 0 .5-7.97 5.2 5.2 0 0 0-9.92-1.3A3.9 3.9 0 0 0 7.6 18.2Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      {/* 流水线：云内一条向前的箭头，表示交付链 */}
      <path
        d="M9.4 12.6h5.2m-1.9-1.9 1.9 1.9-1.9 1.9"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** 按 provider 键取品牌标记，避免调用方写分支。 */
export function ProviderBrand({
  provider,
  size = 20,
}: {
  provider: string;
  size?: number;
}) {
  return provider === "github" ? (
    <BrandGithub size={size} />
  ) : (
    <BrandYunxiao size={size} />
  );
}
