import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router";
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

export function LoginPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const login = useLogin();
  const [secret, setSecret] = useState("");
  const [remaining, setRemaining] = useState(0);

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
      <form className={styles.card} onSubmit={onSubmit}>
        <h1>AI 测试工作台</h1>
        {reason === "expired" ? (
          <AuthBanner tone="info">会话已过期，请重新登录</AuthBanner>
        ) : null}
        {reason === "logged-out" ? (
          <AuthBanner tone="info">已退出登录</AuthBanner>
        ) : null}
        <PasswordField
          value={secret}
          onChange={setSecret}
          error={locked ? undefined : errorMessage}
          disabled={locked || login.isPending}
        />
        {locked ? (
          <p className={styles.countdown} aria-live="polite">
            尝试次数过多，请在 {formatCountdown(remaining)} 后重试
          </p>
        ) : null}
        <Button type="submit" loading={login.isPending} disabled={locked}>
          登录
        </Button>
      </form>
    </div>
  );
}
