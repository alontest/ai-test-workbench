import { useId } from "react";
import styles from "./mascot.module.css";

/**
 * AI 测试工作台吉祥物组件：夜巡猫头鹰探长「鸮鸮 (Inspector Hoot)」。
 *
 * 响应式细节分层（Adaptive LOD）：
 * - `size <= 36`（24px/28px/32px 品牌位、内联徽章位）：自动渲染高对比「头像剪影态」，砍掉细碎肢体，放大护目镜与眼神
 * - `size > 36`（40px~200px 空态、页头、英雄位）：渲染「完整角色态」，包含身体、肢体动作、状态道具与光影层次
 */
export type MascotState =
  | "idle"
  | "watching"
  | "analyzing"
  | "warning"
  | "success"
  | "sleeping";

export type MascotVariant = "owl";

export interface MascotProps {
  state?: MascotState;
  /** 唯一官方角色标识，保留 prop 兼容。 */
  variant?: MascotVariant;
  /** 渲染尺寸（宽高相等）。<= 36 自动走头像剪影态，> 36 走完整角色态。 */
  size?: number;
  /** 无障碍标签；不传则对辅助技术隐藏（纯装饰）。 */
  label?: string;
  className?: string;
}

const ACCENT = "#22C55E";
const ACCENT_BRIGHT = "#4ADE80";
const WARN = "#F59E0B";
const WARN_BRIGHT = "#FBBF24";
const GOLD = "#FACC15";

export function Mascot({
  state = "idle",
  variant = "owl",
  size = 96,
  label,
  className,
}: MascotProps) {
  const uid = useId().replace(/:/g, "");
  const compact = size <= 36;

  return (
    <svg
      viewBox={compact ? "0 0 48 48" : "0 0 120 120"}
      width={size}
      height={size}
      className={[
        styles.mascot,
        styles[state],
        styles[`variant_${variant}`],
        compact ? styles.compact : styles.detailed,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      fill="none"
    >
      <SharedDefs uid={uid} state={state} />
      {compact ? (
        <CompactHead state={state} uid={uid} />
      ) : (
        <OwlFull state={state} uid={uid} />
      )}
    </svg>
  );
}

function SharedDefs({ uid, state }: { uid: string; state: MascotState }) {
  const themeColor = state === "warning" ? WARN : ACCENT;
  const themeBright = state === "warning" ? WARN_BRIGHT : ACCENT_BRIGHT;
  return (
    <defs>
      {/* 羽毛主体渐变（角色自身深岩灰配色，亮/暗主题均具清晰轮廓） */}
      <linearGradient id={`${uid}-body`} x1="25%" y1="10%" x2="80%" y2="95%">
        <stop offset="0%" stopColor="#323846" />
        <stop offset="55%" stopColor="#1E222D" />
        <stop offset="100%" stopColor="#12151C" />
      </linearGradient>

      {/* 头部偏亮立体渐变 */}
      <linearGradient id={`${uid}-head`} x1="20%" y1="5%" x2="75%" y2="95%">
        <stop offset="0%" stopColor="#3F4759" />
        <stop offset="60%" stopColor="#252A37" />
        <stop offset="100%" stopColor="#171A22" />
      </linearGradient>

      {/* 浅灰羽肚面盘 */}
      <linearGradient id={`${uid}-belly`} x1="50%" y1="0%" x2="50%" y2="100%">
        <stop offset="0%" stopColor="#4B5568" />
        <stop offset="100%" stopColor="#2A303D" />
      </linearGradient>

      {/* 护目镜/状态主色发光渐变 */}
      <linearGradient id={`${uid}-glow`} x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor={themeBright} />
        <stop offset="100%" stopColor={themeColor} />
      </linearGradient>

      {/* 镜片深邃反光 */}
      <radialGradient id={`${uid}-lens`} cx="35%" cy="30%" r="70%">
        <stop offset="0%" stopColor="#1E293B" />
        <stop offset="70%" stopColor="#090D16" />
        <stop offset="100%" stopColor="#052E16" />
      </radialGradient>

      {/* 背后氛围光晕 */}
      <radialGradient id={`${uid}-aura`} cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor={themeColor} stopOpacity="0.24" />
        <stop offset="65%" stopColor={themeColor} stopOpacity="0.06" />
        <stop offset="100%" stopColor={themeColor} stopOpacity="0" />
      </radialGradient>
    </defs>
  );
}

/* ============================================================================
 * 小尺寸头像剪影态（size <= 36，用于 24px / 28px / 32px 徽章位）
 * ========================================================================== */
function CompactHead({
  state,
  uid,
}: {
  state: MascotState;
  uid: string;
}) {
  const accent = state === "warning" ? WARN : ACCENT;
  const bright = state === "warning" ? WARN_BRIGHT : ACCENT_BRIGHT;

  return (
    <g className={styles.character}>
        {/* 耳羽簇 */}
        <path
          d={
            state === "warning"
              ? "M8 15 L3 5 L16 11 Z M40 15 L45 5 L32 11 Z"
              : "M10 15 L6 6 L18 12 Z M38 15 L42 6 L30 12 Z"
          }
          fill={`url(#${uid}-head)`}
          stroke={accent}
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        {/* 圆头轮廓 */}
        <rect
          x="6"
          y="10"
          width="36"
          height="32"
          rx="16"
          fill={`url(#${uid}-head)`}
          stroke="#475569"
          strokeWidth="1.5"
        />
        {/* 护目镜大眼框 */}
        <circle
          cx="17.5"
          cy="25"
          r="7.5"
          fill="#0B0F17"
          stroke={accent}
          strokeWidth="2.2"
        />
        <circle
          cx="30.5"
          cy="25"
          r="7.5"
          fill="#0B0F17"
          stroke={accent}
          strokeWidth="2.2"
        />
        <path d="M24.5 25 H25.5" stroke={accent} strokeWidth="2.2" />
        {/* 眼神按状态切换 */}
        {state === "sleeping" ? (
          <>
            <path
              d="M13.5 25.5 Q17.5 28.5 21.5 25.5"
              stroke="#94A3B8"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <path
              d="M26.5 25.5 Q30.5 28.5 34.5 25.5"
              stroke="#94A3B8"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </>
        ) : state === "success" ? (
          <>
            <path
              d="M13.5 26 Q17.5 21.5 21.5 26"
              stroke={bright}
              strokeWidth="2.4"
              strokeLinecap="round"
            />
            <path
              d="M26.5 26 Q30.5 21.5 34.5 26"
              stroke={bright}
              strokeWidth="2.4"
              strokeLinecap="round"
            />
          </>
        ) : (
          <>
            <circle cx="17.5" cy="25" r="3.4" fill={bright} />
            <circle cx="30.5" cy="25" r="3.4" fill={bright} />
            <circle cx="16.2" cy="23.6" r="1.3" fill="#FFFFFF" />
            <circle cx="29.2" cy="23.6" r="1.3" fill="#FFFFFF" />
          </>
        )}
        {/* 琥珀小鸟喙 */}
        <path d="M22 31 L26 31 L24 35 Z" fill={GOLD} />
      </g>
  );
}

/* ============================================================================
 * 唯一官方角色：夜巡猫头鹰探长「鸮鸮 (Inspector Hoot)」
 * ========================================================================== */
function OwlFull({ state, uid }: { state: MascotState; uid: string }) {
  const accent = state === "warning" ? WARN : ACCENT;
  const bright = state === "warning" ? WARN_BRIGHT : ACCENT_BRIGHT;
  const gogglesDown = state === "analyzing";

  // 视线偏移：watching 向右前专注凝视，analyzing 居中锁定
  const pupilDx = state === "watching" ? 2.2 : 0;
  const pupilDy = state === "watching" ? -1 : 0;

  return (
    <g className={styles.Scene}>
      {/* 底部投影与背景微光 */}
      <circle cx="60" cy="60" r="52" fill={`url(#${uid}-aura)`} />
      <ellipse
        className={styles.shadow}
        cx="60"
        cy="108"
        rx="28"
        ry="5"
        fill="#000000"
        opacity="0.45"
      />

      <g className={styles.character}>
        {/* ── 身体与肚皮羽毛层 ── */}
        <rect
          x="31"
          y="54"
          width="58"
          height="48"
          rx="26"
          fill={`url(#${uid}-body)`}
          stroke="#3F4759"
          strokeWidth="1.5"
        />
        {/* 胸前浅色羽肚 */}
        <path
          d="M42 66 C42 57 78 57 78 66 L76 92 C76 98 44 98 44 92 Z"
          fill={`url(#${uid}-belly)`}
          opacity="0.85"
        />
        {/* 胸前 V 字羽毛纹理 */}
        <path
          d="M52 75 L55 78 L58 75 M62 75 L65 78 L68 75 M55 83 L58 86 L61 83 M61 83 L64 86 L67 83"
          stroke="#1E222D"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.75"
        />

        {/* ── 探长小领结与翡翠核心徽章 ── */}
        <path
          d="M51 62 L60 66 L51 70 Z M69 62 L60 66 L69 70 Z"
          fill="#15803D"
          stroke={accent}
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
        <circle
          className={styles.coreGem}
          cx="60"
          cy="66"
          r="3.2"
          fill={bright}
        />

        {/* ── 两只小爪子 ── */}
        <g stroke={GOLD} strokeWidth="2.2" strokeLinecap="round">
          <path d="M46 101 V106 M49 101 V107 M52 101 V106" />
          <path d="M68 101 V106 M71 101 V107 M74 101 V106" />
        </g>

        {/* ── 左右翅膀（随状态切换姿态） ── */}
        {state === "watching" ? (
          <>
            {/* 左翅自然收拢，右翅抬起托腮思考 */}
            <path
              d="M31 62 C23 68 23 86 32 92"
              fill={`url(#${uid}-body)`}
              stroke="#475569"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <path
              className={styles.wingRight}
              d="M88 64 C98 58 95 46 78 52"
              fill={`url(#${uid}-head)`}
              stroke={accent}
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </>
        ) : state === "warning" ? (
          <>
            {/* 告警：双翅向两侧张开炸毛 */}
            <path
              className={styles.wingLeft}
              d="M32 62 C16 54 13 70 26 82"
              fill={`url(#${uid}-head)`}
              stroke={WARN}
              strokeWidth="1.6"
            />
            <path
              className={styles.wingRight}
              d="M88 62 C104 54 107 70 94 82"
              fill={`url(#${uid}-head)`}
              stroke={WARN}
              strokeWidth="1.6"
            />
          </>
        ) : state === "success" ? (
          <>
            {/* 成功：左翅叉腰，右翅高举 PASS 徽章 */}
            <path
              d="M31 62 C22 68 23 86 32 92"
              fill={`url(#${uid}-body)`}
              stroke="#475569"
              strokeWidth="1.5"
            />
            <path
              className={styles.wingRight}
              d="M87 64 C101 52 103 38 92 34"
              fill={`url(#${uid}-head)`}
              stroke={ACCENT}
              strokeWidth="1.6"
            />
          </>
        ) : (
          <>
            {/* 默认/休眠/分析：双翅自然包裹 */}
            <path
              className={styles.wingLeft}
              d="M31 62 C22 68 23 88 33 93"
              fill={`url(#${uid}-body)`}
              stroke="#475569"
              strokeWidth="1.5"
            />
            <path
              className={styles.wingRight}
              d="M89 62 C98 68 97 88 87 93"
              fill={`url(#${uid}-body)`}
              stroke="#475569"
              strokeWidth="1.5"
            />
          </>
        )}

        {/* ── 头部与耳羽簇 ── */}
        <g className={styles.headGroup}>
          {/* 左右耳羽簇：warning 炸开、watching 高竖、sleeping 耷拉 */}
          <path
            className={styles.earLeft}
            d={
              state === "sleeping"
                ? "M36 28 L22 25 L32 36 Z"
                : state === "warning"
                  ? "M35 26 L18 11 L29 33 Z"
                  : state === "watching"
                    ? "M36 26 L24 9 L31 32 Z"
                    : "M36 27 L25 13 L31 33 Z"
            }
            fill={`url(#${uid}-head)`}
            stroke={accent}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            className={styles.earRight}
            d={
              state === "sleeping"
                ? "M84 28 L98 25 L88 36 Z"
                : state === "warning"
                  ? "M85 26 L102 11 L91 33 Z"
                  : state === "watching"
                    ? "M84 26 L96 9 L89 32 Z"
                    : "M84 27 L95 13 L89 33 Z"
            }
            fill={`url(#${uid}-head)`}
            stroke={accent}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />

          {/* 头壳主体 */}
          <rect
            x="27"
            y="20"
            width="66"
            height="46"
            rx="23"
            fill={`url(#${uid}-head)`}
            stroke="#525D72"
            strokeWidth="1.6"
          />
          {/* 头顶高光弧 */}
          <path
            d="M42 24 Q60 21 78 24"
            stroke="#FFFFFF"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.18"
          />

          {/* 猫头鹰双圆眼盘（Facial Disc） */}
          <circle
            cx="47"
            cy="44"
            r="13.5"
            fill="#141821"
            stroke="#3B4456"
            strokeWidth="1.4"
          />
          <circle
            cx="73"
            cy="44"
            r="13.5"
            fill="#141821"
            stroke="#3B4456"
            strokeWidth="1.4"
          />

          {/* ── 眼睛层（按六态切换丰富神态） ── */}
          {state === "sleeping" ? (
            <g stroke="#94A3B8" strokeWidth="2.4" strokeLinecap="round">
              <path d="M39 45 Q47 51 55 45" />
              <path d="M65 45 Q73 51 81 45" />
            </g>
          ) : state === "success" ? (
            <g stroke={ACCENT_BRIGHT} strokeWidth="2.8" strokeLinecap="round">
              <path d="M39 46 Q47 37 55 46" />
              <path d="M65 46 Q73 37 81 46" />
            </g>
          ) : (
            <g className={styles.eyes}>
              {/* 外虹膜环 */}
              <circle
                cx={47 + pupilDx * 0.4}
                cy={44 + pupilDy * 0.4}
                r={state === "warning" ? "8.5" : "9.5"}
                fill="#090D16"
                stroke={accent}
                strokeWidth="2.2"
              />
              <circle
                cx={73 + pupilDx * 0.4}
                cy={44 + pupilDy * 0.4}
                r={state === "warning" ? "8.5" : "9.5"}
                fill="#090D16"
                stroke={accent}
                strokeWidth="2.2"
              />

              {/* 瞳孔：warning 收缩告警，watching 聚焦 */}
              <circle
                cx={47 + pupilDx}
                cy={44 + pupilDy}
                r={state === "warning" ? "3.2" : "5.2"}
                fill={bright}
              />
              <circle
                cx={73 + pupilDx}
                cy={44 + pupilDy}
                r={state === "warning" ? "3.2" : "5.2"}
                fill={bright}
              />

              {/* 双眼神高光点（灵魂所在！） */}
              <circle
                cx={44.5 + pupilDx}
                cy={41.5 + pupilDy}
                r="2.1"
                fill="#FFFFFF"
              />
              <circle
                cx={49.5 + pupilDx}
                cy={46.5 + pupilDy}
                r="0.9"
                fill="#FFFFFF"
                opacity="0.8"
              />
              <circle
                cx={70.5 + pupilDx}
                cy={41.5 + pupilDy}
                r="2.1"
                fill="#FFFFFF"
              />
              <circle
                cx={75.5 + pupilDx}
                cy={46.5 + pupilDy}
                r="0.9"
                fill="#FFFFFF"
                opacity="0.8"
              />
            </g>
          )}

          {/* 琥珀立体小弯喙 */}
          <path
            d="M56 50 L64 50 L60 57 Z"
            fill={GOLD}
            stroke="#B45309"
            strokeWidth="1"
            strokeLinejoin="round"
          />

          {/* ── 战术测试护目镜（analyzing 拉下戴在眼上，其他状态架在额头） ── */}
          {gogglesDown ? (
            <g className={styles.gogglesActive}>
              {/* 护目镜绑带 */}
              <path
                d="M26 43 H33 M87 43 H94 M59 43 H61"
                stroke={ACCENT_BRIGHT}
                strokeWidth="2.6"
                strokeLinecap="round"
              />
              {/* 左右 HUD 镜框 */}
              <circle
                cx="47"
                cy="44"
                r="13.5"
                fill="#052E16"
                fillOpacity="0.38"
                stroke={ACCENT_BRIGHT}
                strokeWidth="2.6"
              />
              <circle
                cx="73"
                cy="44"
                r="13.5"
                fill="#052E16"
                fillOpacity="0.38"
                stroke={ACCENT_BRIGHT}
                strokeWidth="2.6"
              />
              {/* 旋转扫描准星弧 */}
              <circle
                className={styles.scanRingLeft}
                cx="47"
                cy="44"
                r="10.5"
                stroke="#86EFAC"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeDasharray="16 18"
                style={{ transformOrigin: "47px 44px" }}
              />
              <circle
                className={styles.scanRingRight}
                cx="73"
                cy="44"
                r="10.5"
                stroke="#86EFAC"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeDasharray="16 18"
                style={{ transformOrigin: "73px 44px" }}
              />
              {/* HUD 十字瞄准刻度 */}
              <path
                d="M47 35 V38 M47 50 V53 M38 44 H41 M53 44 H56 M73 35 V38 M73 50 V53 M64 44 H67 M79 44 H82"
                stroke="#BBF7D0"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </g>
          ) : (
            <g className={styles.gogglesResting}>
              {/* 架在额头上的护目镜带与双镜筒 */}
              <path
                d="M29 28 Q60 22 91 28"
                stroke="#475569"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <rect
                x="36"
                y="18"
                width="19"
                height="12"
                rx="6"
                fill={`url(#${uid}-lens)`}
                stroke={accent}
                strokeWidth="1.8"
              />
              <rect
                x="65"
                y="18"
                width="19"
                height="12"
                rx="6"
                fill={`url(#${uid}-lens)`}
                stroke={accent}
                strokeWidth="1.8"
              />
              <path d="M55 24 H65" stroke={accent} strokeWidth="2.2" />
              {/* 镜片斜高光 */}
              <path
                d="M40 21 L44 21 M69 21 L73 21"
                stroke="#FFFFFF"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.55"
              />
            </g>
          )}
        </g>

        {/* ── 状态专属道具层（Props & Overlays） ── */}
        {state === "watching" && (
          <g className={styles.propWatching}>
            {/* 头顶雷达感应波 */}
            <path
              d="M95 20 Q103 24 101 33"
              stroke={ACCENT_BRIGHT}
              strokeWidth="1.8"
              strokeLinecap="round"
            />
            <path
              d="M99 15 Q110 21 107 35"
              stroke={ACCENT}
              strokeWidth="1.5"
              strokeLinecap="round"
              opacity="0.65"
            />
          </g>
        )}

        {state === "analyzing" && (
          <g className={styles.propAnalyzing}>
            {/* 底部悬浮代码/日志扫描流卡片 */}
            <rect
              x="84"
              y="68"
              width="28"
              height="22"
              rx="5"
              fill="#090D16"
              stroke={ACCENT}
              strokeWidth="1.4"
            />
            <path
              d="M89 74 H103 M89 79 H107 M89 84 H98"
              stroke={ACCENT_BRIGHT}
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </g>
        )}

        {state === "warning" && (
          <g className={styles.propWarning}>
            {/* 头顶琥珀色告警三角牌 */}
            <path
              d="M60 3 L69 18 H51 Z"
              fill="#451A03"
              stroke={WARN_BRIGHT}
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
            <path
              d="M60 8.5 V12.5 M60 15.2 V15.5"
              stroke={WARN_BRIGHT}
              strokeWidth="2"
              strokeLinecap="round"
            />
          </g>
        )}

        {state === "success" && (
          <g className={styles.propSuccess}>
            {/* 右翅旁漂浮的翠绿 PASS 印章盾牌 */}
            <circle
              cx="98"
              cy="28"
              r="12"
              fill="#052E16"
              stroke={ACCENT_BRIGHT}
              strokeWidth="2"
            />
            <path
              d="M92.5 28 L96.5 32 L104 24"
              stroke={ACCENT_BRIGHT}
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* 星芒点缀 */}
            <path
              d="M18 26 V32 M15 29 H21 M105 52 V56 M103 54 H107"
              stroke={ACCENT_BRIGHT}
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </g>
        )}

        {state === "sleeping" && (
          <g
            className={styles.propSleeping}
            fill="#94A3B8"
            fontFamily="JetBrains Mono, monospace"
            fontWeight="700"
          >
            <text x="88" y="34" fontSize="10" opacity="0.55">
              z
            </text>
            <text x="96" y="23" fontSize="13" opacity="0.75">
              Z
            </text>
            <text x="105" y="12" fontSize="15" opacity="0.9">
              Z
            </text>
          </g>
        )}
      </g>
    </g>
  );
}
