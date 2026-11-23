import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { FormField } from "../../components/ui/FormField";
import { Input, Textarea } from "../../components/ui/Input";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { Select } from "../../components/ui/Select";
import { apiFetch, queryString } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { queryKeys } from "../../lib/api/keys";
import styles from "./extensions.module.css";

interface Page<T> {
  items: T[];
  nextCursor?: string | null;
}

interface Project {
  projectId: number;
  name: string;
}

interface SkillVersion {
  versionId: string;
  version: number;
  changeSummary: string;
  sourceType: string;
  createdAt: string;
}

interface Skill {
  skillId: string;
  scope: "global" | "project";
  projectId: number | null;
  slug: string;
  name: string;
  domain: string;
  description: string;
  contentMd: string;
  currentVersion: number;
  isBuiltin: boolean;
  versions?: SkillVersion[];
}

interface Provider {
  providerId: number;
  name: string;
}

interface Model {
  modelId: number;
  modelName: string;
  displayName: string;
}

interface Approval {
  approvalId: string;
  unifiedDiff: string;
  status: string;
  rationale: string;
}

const EMPTY_CREATE = {
  scope: "project",
  slug: "",
  name: "",
  description: "",
  contentMd: "",
};

function errorMessage(error: unknown, fallback: string): string {
  return isApiError(error) ? error.message : fallback;
}

export function SkillsPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_CREATE);
  const [draft, setDraft] = useState<{
    skillId: string;
    baseVersion: number;
    text: string;
  } | null>(null);
  const [instruction, setInstruction] = useState("");
  const [providerId, setProviderId] = useState("");
  const [modelId, setModelId] = useState("");
  const [proposal, setProposal] = useState<Approval | null>(null);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<Page<Project>>(`/projects${queryString({ limit: 100 })}`),
  });
  const effectiveProjectId = projectId ?? projectsQuery.data?.items[0]?.projectId ?? null;

  const skillsQuery = useQuery({
    queryKey: queryKeys.skills(effectiveProjectId ?? undefined),
    queryFn: () =>
      apiFetch<Page<Skill>>(
        `/skills${queryString({ projectId: effectiveProjectId ?? undefined })}`,
      ),
    enabled: projectsQuery.isSuccess,
  });

  const activeSkillId = selectedSkillId ?? skillsQuery.data?.items[0]?.skillId ?? null;
  const detailQuery = useQuery({
    queryKey: queryKeys.skill(activeSkillId ?? ""),
    queryFn: () => apiFetch<Skill>(`/skills/${activeSkillId}`),
    enabled: activeSkillId !== null,
  });

  const providersQuery = useQuery({
    queryKey: queryKeys.providers,
    queryFn: () => apiFetch<Page<Provider>>(`/providers${queryString({ limit: 100 })}`),
  });
  const modelsQuery = useQuery({
    queryKey: queryKeys.providerModels(Number(providerId)),
    queryFn: () =>
      apiFetch<Page<Model>>(
        `/providers/${providerId}/models${queryString({ limit: 100 })}`,
      ),
    enabled: providerId !== "",
  });

  const createSkill = useMutation({
    mutationFn: () =>
      apiFetch<Skill>("/skills", {
        method: "POST",
        body: JSON.stringify({
          scope: createForm.scope,
          projectId: createForm.scope === "project" ? effectiveProjectId : null,
          slug: createForm.slug,
          name: createForm.name,
          description: createForm.description,
          contentMd: createForm.contentMd,
        }),
      }),
    onSuccess: (skill) => {
      setCreating(false);
      setCreateForm(EMPTY_CREATE);
      setSelectedSkillId(skill.skillId);
      void queryClient.invalidateQueries({ queryKey: queryKeys.skills() });
    },
  });

  const saveSkill = useMutation({
    mutationFn: () => {
      if (!detailQuery.data) {
        throw new Error("no skill");
      }
      return apiFetch<Skill>(`/skills/${detailQuery.data.skillId}`, {
        method: "PUT",
        body: JSON.stringify({ contentMd: draft?.text ?? detailQuery.data.contentMd }),
      });
    },
    onSuccess: (skill) => {
      setDraft(null);
      queryClient.setQueryData(queryKeys.skill(skill.skillId), skill);
      void queryClient.invalidateQueries({ queryKey: queryKeys.skills() });
    },
  });

  const rollback = useMutation({
    mutationFn: (targetVersion: number) =>
      apiFetch<Skill>(`/skills/${activeSkillId}/rollback`, {
        method: "POST",
        body: JSON.stringify({ targetVersion }),
      }),
    onSuccess: (skill) => {
      setDraft(null);
      queryClient.setQueryData(queryKeys.skill(skill.skillId), skill);
      void queryClient.invalidateQueries({ queryKey: queryKeys.skills() });
    },
  });

  const propose = useMutation({
    mutationFn: () =>
      apiFetch<Approval>(`/skills/${activeSkillId}/proposals`, {
        method: "POST",
        body: JSON.stringify({
          projectId: effectiveProjectId,
          modelId: Number(modelId),
          instruction,
        }),
      }),
    onSuccess: setProposal,
  });

  const detail = detailQuery.data;
  const contentText =
    detail &&
    draft &&
    draft.skillId === detail.skillId &&
    draft.baseVersion === detail.currentVersion
      ? draft.text
      : (detail?.contentMd ?? "");

  return (
    <PageContainer tier="xl" className={styles.section}>
      <PageHeader
        title="QA 技能库"
        description="技能是人类编写的测试方法论资产。AI 只能提交 Diff 提案，经审批中心人工确认后才落盘。"
        actions={
          <Button type="button" onClick={() => setCreating((value) => !value)}>
            新建技能
          </Button>
        }
      />

      <section className={styles.toolbar} aria-label="技能筛选">
        <FormField label="项目">
          <Select
            aria-label="项目"
            value={effectiveProjectId ? String(effectiveProjectId) : ""}
            placeholder="选择项目"
            options={(projectsQuery.data?.items ?? []).map((project) => ({
              value: String(project.projectId),
              label: project.name,
            }))}
            onChange={(value) => {
              setProjectId(value ? Number(value) : null);
              setSelectedSkillId(null);
            }}
          />
        </FormField>
      </section>

      {creating ? (
        <form
          className={styles.panel}
          aria-label="新建技能"
          onSubmit={(event) => {
            event.preventDefault();
            createSkill.mutate();
          }}
        >
          <FormField label="作用域">
            <Select
              aria-label="作用域"
              value={createForm.scope}
              options={[
                { value: "project", label: "项目级 project" },
                { value: "global", label: "全局 global" },
              ]}
              onChange={(value) =>
                setCreateForm((form) => ({ ...form, scope: value }))
              }
            />
          </FormField>
          <FormField label="技能标识（slug）" required>
            <Input
              aria-label="技能标识"
              value={createForm.slug}
              onChange={(event) =>
                setCreateForm((form) => ({ ...form, slug: event.target.value }))
              }
            />
          </FormField>
          <FormField label="技能名称" required>
            <Input
              aria-label="技能名称"
              value={createForm.name}
              onChange={(event) =>
                setCreateForm((form) => ({ ...form, name: event.target.value }))
              }
            />
          </FormField>
          <FormField label="一句话说明" required>
            <Input
              aria-label="技能说明"
              value={createForm.description}
              onChange={(event) =>
                setCreateForm((form) => ({
                  ...form,
                  description: event.target.value,
                }))
              }
            />
          </FormField>
          <FormField label="初始 Markdown" required>
            <Textarea
              aria-label="初始 Markdown"
              rows={6}
              value={createForm.contentMd}
              onChange={(event) =>
                setCreateForm((form) => ({
                  ...form,
                  contentMd: event.target.value,
                }))
              }
            />
          </FormField>
          {createSkill.isError ? (
            <ErrorState
              message={errorMessage(createSkill.error, "创建技能失败")}
              retryable={false}
            />
          ) : null}
          <div className={styles.actions}>
            <Button type="submit" loading={createSkill.isPending}>
              保存技能
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setCreating(false)}
            >
              取消
            </Button>
          </div>
        </form>
      ) : null}

      {skillsQuery.isPending ? (
        <Spinner label="加载技能" />
      ) : skillsQuery.isError ? (
        <ErrorState
          message="无法加载技能列表"
          onRetry={() => void skillsQuery.refetch()}
        />
      ) : (
        <div className={styles.split}>
          <aside className={styles.list} aria-label="技能列表">
            {(skillsQuery.data?.items ?? []).length === 0 ? (
              <p className={styles.meta}>当前项目还没有技能。</p>
            ) : (
              (skillsQuery.data?.items ?? []).map((skill) => (
                <button
                  key={skill.skillId}
                  type="button"
                  className={[
                    styles.listItem,
                    skill.skillId === activeSkillId ? styles.listItemActive : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  aria-pressed={skill.skillId === activeSkillId}
                  onClick={() => {
                    setSelectedSkillId(skill.skillId);
                    setProposal(null);
                    setDraft(null);
                  }}
                >
                  <span className={styles.listTitle}>{skill.name}</span>
                  <span className={styles.listMeta}>
                    <code>{skill.slug}</code>
                    <Badge
                      label={skill.scope === "global" ? "global" : "project"}
                      tone={skill.scope === "global" ? "info" : "neutral"}
                    />
                    <span>v{skill.currentVersion}</span>
                  </span>
                </button>
              ))
            )}
          </aside>

          <section className={styles.detail} aria-label="技能详情">
            {detailQuery.isPending && activeSkillId ? (
              <Spinner label="加载技能详情" />
            ) : detailQuery.isError ? (
              <ErrorState
                message="无法加载技能详情"
                onRetry={() => void detailQuery.refetch()}
              />
            ) : !detail ? (
              <p className={styles.meta}>选择左侧技能查看详情。</p>
            ) : (
              <>
                <header className={styles.detailHead}>
                  <h2>{detail.name}</h2>
                  <p className={styles.meta}>{detail.description}</p>
                </header>

                <FormField label="技能正文（Markdown）">
                  <Textarea
                    aria-label="技能正文"
                    rows={14}
                    value={contentText}
                    onChange={(event) =>
                      setDraft({
                        skillId: detail.skillId,
                        baseVersion: detail.currentVersion,
                        text: event.target.value,
                      })
                    }
                  />
                </FormField>
                {saveSkill.isError ? (
                  <ErrorState
                    message={errorMessage(saveSkill.error, "保存失败")}
                    retryable={false}
                  />
                ) : null}
                <div className={styles.actions}>
                  <Button
                    type="button"
                    loading={saveSkill.isPending}
                    onClick={() => saveSkill.mutate()}
                  >
                    保存正文
                  </Button>
                </div>

                <section className={styles.subsection} aria-label="版本历史">
                  <h3>版本历史</h3>
                  <ul className={styles.versionList}>
                    {(detail.versions ?? []).map((version) => (
                      <li key={version.versionId} className={styles.versionRow}>
                        <span>
                          v{version.version} · {version.changeSummary} ·{" "}
                          {version.sourceType}
                        </span>
                        {version.version === detail.currentVersion ? (
                          <Badge label="当前版本" tone="success" />
                        ) : (
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => rollback.mutate(version.version)}
                          >
                            回滚到此版本
                          </Button>
                        )}
                      </li>
                    ))}
                  </ul>
                  {rollback.isError ? (
                    <ErrorState
                      message={errorMessage(rollback.error, "回滚失败")}
                      retryable={false}
                    />
                  ) : null}
                </section>

                <section className={styles.subsection} aria-label="AI 协助修订">
                  <h3>AI 协助修订（生成 Diff 提案）</h3>
                  <p className={styles.meta}>
                    提案不会直接改动技能正文，而是生成待审批的 Unified Diff。
                  </p>
                  <FormField label="修订指令">
                    <Textarea
                      aria-label="修订指令"
                      rows={3}
                      value={instruction}
                      onChange={(event) => setInstruction(event.target.value)}
                    />
                  </FormField>
                  <div className={styles.inlineFields}>
                    <FormField label="提供商">
                      <Select
                        aria-label="提供商"
                        value={providerId}
                        placeholder="选择提供商"
                        options={(providersQuery.data?.items ?? []).map(
                          (provider) => ({
                            value: String(provider.providerId),
                            label: provider.name,
                          }),
                        )}
                        onChange={(value) => {
                          setProviderId(value);
                          setModelId("");
                        }}
                      />
                    </FormField>
                    <FormField label="模型">
                      <Select
                        aria-label="模型"
                        value={modelId}
                        placeholder="选择模型"
                        options={(modelsQuery.data?.items ?? []).map((model) => ({
                          value: String(model.modelId),
                          label: model.displayName || model.modelName,
                        }))}
                        onChange={setModelId}
                      />
                    </FormField>
                  </div>
                  <div className={styles.actions}>
                    <Button
                      type="button"
                      loading={propose.isPending}
                      disabled={!instruction.trim() || !modelId}
                      onClick={() => propose.mutate()}
                    >
                      生成 Diff 提案
                    </Button>
                  </div>
                  {propose.isError ? (
                    <ErrorState
                      message={errorMessage(propose.error, "生成提案失败")}
                      retryable={false}
                    />
                  ) : null}
                  {proposal ? (
                    <div className={styles.proposal} data-testid="proposal-diff">
                      <p className={styles.meta}>
                        提案已进入审批中心，状态 {proposal.status}。
                      </p>
                      <pre className={styles.diff}>{proposal.unifiedDiff}</pre>
                      <Link to="/extensions/approvals" className={styles.jump}>
                        前往审批中心
                      </Link>
                    </div>
                  ) : null}
                </section>
              </>
            )}
          </section>
        </div>
      )}
    </PageContainer>
  );
}
