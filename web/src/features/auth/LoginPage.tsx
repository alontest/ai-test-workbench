import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router";
import {
  FeatureCalls,
  FeatureKnowledge,
  FeatureRepo,
  IconCheck,
} from "../../components/icons";
import { Mascot, type MascotState } from "../../components/mascot/Mascot";
import { Button } from "../../components/ui/Button";
import { isApiError } from "../../lib/api/errors";
import { safeNextPath } from "../../lib/safeNext";
import { AuthBanner } from "./AuthBanner";
import styles from "./LoginPage.module.css";
import { PasswordField } from "./PasswordField";
import { useLogin } from "./useLogin";

function formatCountdown(seconds: number): string {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60)
    .toString()
    .padStart(2, "0");
  const rest = (safe % 60).toString().padStart(2, "0");
  return `${minutes}:${rest}`;
}

const CAPABILITIES = [
  {
    icon: FeatureKnowledge,
    title: "200k 字符预算与知识注入",
    detail: "调用前核对预算，超限直接拦截，不偷偷截断。",
  },
  {
    icon: FeatureRepo,
    title: "云效 / GitHub 只读浏览",
    detail: "令牌只由基座持有，回显一律掩码。",
  },
  {
    icon: FeatureCalls,
    title: "全链路调用留痕与审计",
    detail: "每次调用都有记录，提示词与耗时随时可查。",
  },
] as const;

export function LoginPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const login = useLogin();
  const [secret, setSecret] = useState("");
  const [remaining, setRemaining] = useState(0);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (remaining <= 0) {
      return;
    }
    const timer = window.setTimeout(() => {
      setRemaining((seconds) => Math.max(0, seconds - 1));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [remaining]);

  const locked = remaining > 0;
  const reason = params.get("reason");
  const next = useMemo(
    () => safeNextPath(params.get("next")),
    [params],
  );

  const errorMessage = login.isError
    ? isApiError(login.error)
      ? login.error.message
      : "口令错误，请重试。"
    : undefined;

  const mascotState: MascotState =
    locked || errorMessage
      ? "warning"
      : reason === "expired"
        ? "sleeping"
        : focused || secret.length > 0
          ? "watching"
          : "idle";

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await login.mutateAsync(secret);
      navigate(next, { replace: true });
    } catch (error) {
      if (isApiError(error) && error.code === "login_locked") {
        const retry =
          Number(error.details[0]?.retryAfterSeconds ?? 0) || 0;
        setRemaining(retry);
      }
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.stage}>
        <aside className={styles.showcase} aria-label="鸮鸮夜巡探案台">
          <div className={styles.mascotWrap}>
            <Mascot size={140} state={mascotState} label="鸮鸮" />
          </div>
          <div className={styles.showcaseCopy}>
            <span className={styles.eyebrow}>LOCAL INSPECTOR</span>
            <h2 className={styles.showcaseTitle}>夜巡探案台</h2>
            <p className={styles.showcaseText}>
              测试工程师的夜间值班室。读需求、抓 Bug、翻日志、审 SQL，
              每一次判断都在这里留下证据。
            </p>
          </div>
          <ul className={styles.capabilities}>
            {CAPABILITIES.map(({ icon: Icon, title, detail }) => (
              <li key={title} className={styles.capability}>
                <span className={styles.capabilityIcon}>
                  <Icon size={20} />
                </span>
                <span className={styles.capabilityBody}>
                  <strong>{title}</strong>
                  <span>{detail}</span>
                </span>
                <IconCheck size={16} className={styles.capabilityCheck} />
              </li>
            ))}
          </ul>
        </aside>

        <form className={styles.card} onSubmit={onSubmit}>
          <div className={styles.brand}>
            <span className={styles.mark} aria-hidden="true">
              V
            </span>
            <span className={styles.brandName}>Vigil · 鸮巡</span>
          </div>

          <div className={styles.intro}>
            <h1>登录工作台</h1>
            <p>输入部署时设置的管理员口令，登录后才能访问工作台页面。</p>
          </div>

          {reason === "expired" ? (
            <AuthBanner tone="info">会话已过期，请重新登录</AuthBanner>
          ) : null}
          {reason === "logged-out" ? (
            <AuthBanner tone="info">已退出登录</AuthBanner>
          ) : null}

          <div
            onFocusCapture={() => setFocused(true)}
            onBlurCapture={() => setFocused(false)}
          >
            <PasswordField
              value={secret}
              onChange={setSecret}
              error={locked ? undefined : errorMessage}
              disabled={locked || login.isPending}
              hint="口令由部署环境变量提供，不会明文回显，也不会写入日志。"
            />
          </div>

          {locked ? (
            <p className={styles.countdown} aria-live="polite">
              尝试次数过多，请在 {formatCountdown(remaining)} 后重试
            </p>
          ) : null}

          <Button type="submit" loading={login.isPending} disabled={locked}>
            登录
          </Button>

          <p className={styles.foot}>
            单用户自托管：系统不提供注册与找回口令，口令由部署侧维护。
          </p>
        </form>
      </div>
    </div>
  );
}
