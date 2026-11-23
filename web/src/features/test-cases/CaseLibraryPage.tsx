import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState } from "../../components/ui/Feedback";
import { FormField } from "../../components/ui/FormField";
import { Input, Textarea } from "../../components/ui/Input";
import { Spinner } from "../../components/ui/Loading";
import { Select } from "../../components/ui/Select";
import { apiFetch, apiFetchText, queryString } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { queryKeys } from "../../lib/api/keys";
import styles from "./case-library.module.css";

interface Page<T> {
  items: T[];
}

interface Project {
  projectId: number;
  name: string;
}

interface Skill {
  skillId: string;
  name: string;
  domain: string;
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

interface KbEntryRef {
  kbId: string;
  kbName: string;
  code: string;
  title: string;
  matchSource: "direct" | "neighbor_1hop";
  viaCode?: string | null;
}

interface CodePathRef {
  path: string;
  source: "kb_code_path" | "recent_repo_read" | "input_path_mention";
  linkedKbCodes: string[];
}

interface Recommendation {
  recommendedKbEntries: KbEntryRef[];
  recommendedCodePaths: CodePathRef[];
}

interface Checkpoint {
  checkpointId: string;
  module: string;
  scenario: string;
  category: string;
  priority: string;
  rationale: string;
  kbCodes: string[];
  codePaths: string[];
}

interface Plan {
  planId: string;
  checkpoints: Checkpoint[];
}

interface KbLink {
  kbId: string;
  kbNameKey: string;
  code: string;
  title: string;
}

interface CaseStep {
  stepNo: number;
  action: string;
  expected: string;
}

interface TestCase {
  caseId: string;
  caseCode: string;
  module: string;
  title: string;
  priority: string;
  caseType: string;
  preconditions: string[];
  steps: CaseStep[];
  expectedSummary: string;
  kbLinks: KbLink[];
  codePaths: string[];
  staleStatus: "fresh" | "stale";
  staleReasons: string[];
  staleDetails: { code: string; reason: string; message: string }[];
}

interface ModuleNode {
  name: string;
  count: number;
  children: ModuleNode[];
}

interface CaseListResponse {
  items: TestCase[];
  summary: {
    totalCount: number;
    staleCount: number;
    moduleTree: ModuleNode[];
  };
}

const MATCH_SOURCE_LABEL: Record<string, string> = {
  direct: "direct 直命中",
  neighbor_1hop: "neighbor_1hop 一跳邻居",
};

const CODE_PATH_LABEL: Record<string, string> = {
  kb_code_path: "kb_code_path",
  recent_repo_read: "recent_repo_read",
  input_path_mention: "input_path_mention",
};

const PRIORITY_OPTIONS = ["", "P0", "P1", "P2", "P3"].map((value) => ({
  value,
  label: value === "" ? "全部优先级" : value,
}));

function errorMessage(error: unknown, fallback: string): string {
  return isApiError(error) ? error.message : fallback;
}

function kbEntryKey(entry: KbEntryRef): string {
  return `${entry.kbId}:${entry.code}`;
}

function toggle(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

function groupKbRefs(entries: KbEntryRef[], selected: string[]) {
  const merged = new Map<string, string[]>();
  for (const entry of entries) {
    if (!selected.includes(kbEntryKey(entry))) {
      continue;
    }
    const codes = merged.get(entry.kbId) ?? [];
    if (!codes.includes(entry.code)) {
      codes.push(entry.code);
    }
    merged.set(entry.kbId, codes);
  }
  return [...merged.entries()].map(([kbId, entryCodes]) => ({ kbId, entryCodes }));
}

function CaseTable({
  cases,
  expandedId,
  onToggleSteps,
  onAcknowledge,
  onDelete,
}: {
  cases: TestCase[];
  expandedId: string | null;
  onToggleSteps: (caseId: string) => void;
  onAcknowledge: (caseId: string) => void;
  onDelete: (caseId: string) => void;
}) {
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th scope="col">编号</th>
          <th scope="col">模块</th>
          <th scope="col">标题</th>
          <th scope="col">优先级</th>
          <th scope="col">类型</th>
          <th scope="col">溯源锚点</th>
          <th scope="col">状态</th>
          <th scope="col">操作</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((item) => (
          <Fragment key={item.caseId}>
            <tr>
              <td>
                <code>{item.caseCode}</code>
              </td>
              <td>{item.module}</td>
              <td>{item.title}</td>
              <td>{item.priority}</td>
              <td>{item.caseType}</td>
              <td>
                <span className={styles.pills}>
                  {item.kbLinks.map((link) => (
                    <span key={link.code} className={styles.pill}>
                      {link.code}
                    </span>
                  ))}
                  {item.codePaths.map((path) => (
                    <span key={path} className={styles.pillMono}>
                      {path}
                    </span>
                  ))}
                </span>
              </td>
              <td>
                {item.staleStatus === "stale" ? (
                  <span className={styles.staleCell}>
                    <Badge label="待复核" tone="danger" />
                    <span className={styles.staleReason}>
                      {item.staleDetails.map((detail) => detail.message).join(" ")}
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => onAcknowledge(item.caseId)}
                    >
                      确认复核
                    </Button>
                  </span>
                ) : (
                  <Badge label="fresh" tone="success" />
                )}
              </td>
              <td>
                <span className={styles.rowActions}>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => onToggleSteps(item.caseId)}
                  >
                    {expandedId === item.caseId ? "收起步骤" : "查看步骤"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => onDelete(item.caseId)}
                  >
                    删除
                  </Button>
                </span>
              </td>
            </tr>
            {expandedId === item.caseId ? (
              <tr>
                <td colSpan={8}>
                  <div className={styles.steps}>
                    <strong>前置条件</strong>
                    <p>{item.preconditions.join("；") || "无"}</p>
                    <ol>
                      {item.steps.map((step) => (
                        <li key={step.stepNo}>
                          {step.action} → 预期：{step.expected}
                        </li>
                      ))}
                    </ol>
                    <p className={styles.meta}>总体预期：{item.expectedSummary}</p>
                  </div>
                </td>
              </tr>
            ) : null}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}

function TreeNode({
  node,
  path,
  cases,
}: {
  node: ModuleNode;
  path: string;
  cases: TestCase[];
}) {
  const fullPath = path ? `${path}/${node.name}` : node.name;
  const directCases = cases.filter((item) => item.module === fullPath);
  const types = [...new Set(directCases.map((item) => item.caseType))].sort();
  return (
    <li>
      <span className={styles.treeModule}>
        {node.name} <span className={styles.treeCount}>{node.count}</span>
      </span>
      {types.length > 0 ? (
        <ul className={styles.tree}>
          {types.map((type) => (
            <li key={type}>
              <span className={styles.treeType}>{type}</span>
              <ul className={styles.tree}>
                {directCases
                  .filter((item) => item.caseType === type)
                  .map((item) => (
                    <li key={item.caseId} className={styles.treeCase}>
                      <code>{item.caseCode}</code> {item.title}
                      {item.staleStatus === "stale" ? (
                        <Badge label="待复核" tone="danger" />
                      ) : null}
                    </li>
                  ))}
              </ul>
            </li>
          ))}
        </ul>
      ) : null}
      {node.children.length > 0 ? (
        <ul className={styles.tree}>
          {node.children.map((child) => (
            <TreeNode
              key={child.name}
              node={child}
              path={fullPath}
              cases={cases}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function CaseLibraryPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [staleOnly, setStaleOnly] = useState(false);
  const [priority, setPriority] = useState("");
  const [keyword, setKeyword] = useState("");
  const [view, setView] = useState<"table" | "tree">("table");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [generatorOpen, setGeneratorOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [requirementText, setRequirementText] = useState("");
  const [skillId, setSkillId] = useState("");
  const [providerId, setProviderId] = useState("");
  const [modelId, setModelId] = useState("");
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [selectedKb, setSelectedKb] = useState<string[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [selectedCheckpoints, setSelectedCheckpoints] = useState<string[]>([]);
  const [generatedCount, setGeneratedCount] = useState<number | null>(null);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<Page<Project>>(`/projects${queryString({ limit: 100 })}`),
  });
  const activeProjectId =
    projectId ?? projectsQuery.data?.items[0]?.projectId ?? null;
  const filters = { staleOnly, priority, keyword };

  const casesQuery = useQuery({
    queryKey: queryKeys.testCases(activeProjectId ?? 0, filters),
    queryFn: () =>
      apiFetch<CaseListResponse>(
        `/projects/${activeProjectId}/test-cases${queryString({
          staleOnly: staleOnly || undefined,
          priority: priority || undefined,
          q: keyword || undefined,
        })}`,
      ),
    enabled: activeProjectId !== null,
  });

  const skillsQuery = useQuery({
    queryKey: queryKeys.skills(activeProjectId ?? undefined),
    queryFn: () =>
      apiFetch<Page<Skill>>(
        `/skills${queryString({ projectId: activeProjectId ?? undefined, domain: "test-case" })}`,
      ),
    enabled: activeProjectId !== null,
  });
  const providersQuery = useQuery({
    queryKey: queryKeys.providers,
    queryFn: () => apiFetch<Page<Provider>>(`/providers${queryString({ limit: 100 })}`),
    enabled: generatorOpen,
  });
  const modelsQuery = useQuery({
    queryKey: queryKeys.providerModels(Number(providerId)),
    queryFn: () =>
      apiFetch<Page<Model>>(`/providers/${providerId}/models${queryString({ limit: 100 })}`),
    enabled: generatorOpen && providerId !== "",
  });

  const cases = casesQuery.data?.items ?? [];
  const summary = casesQuery.data?.summary;

  const recommend = useMutation({
    mutationFn: () =>
      apiFetch<Recommendation>(
        `/projects/${activeProjectId}/context-recommendations`,
        {
          method: "POST",
          body: JSON.stringify({ text: `${title}\n${requirementText}` }),
        },
      ),
    onSuccess: (result) => {
      setRecommendation(result);
      setSelectedKb(result.recommendedKbEntries.map(kbEntryKey));
      setSelectedPaths(result.recommendedCodePaths.map((item) => item.path));
    },
  });

  const createPlan = useMutation({
    mutationFn: () =>
      apiFetch<Plan>(`/projects/${activeProjectId}/test-case-designs/plan`, {
        method: "POST",
        body: JSON.stringify({
          modelId: Number(modelId),
          skillId: skillId || undefined,
          title,
          requirementText,
          kbRefs: recommendation
            ? groupKbRefs(recommendation.recommendedKbEntries, selectedKb)
            : [],
          codePaths: selectedPaths,
        }),
      }),
    onSuccess: (result) => {
      setPlan(result);
      setSelectedCheckpoints(result.checkpoints.map((item) => item.checkpointId));
      setGeneratedCount(null);
    },
  });

  const generate = useMutation({
    mutationFn: () => {
      if (!plan) {
        throw new Error("no plan");
      }
      return apiFetch<{ generatedCount: number }>(
        `/test-case-designs/${plan.planId}/generate`,
        {
          method: "POST",
          body: JSON.stringify({
            modelId: Number(modelId),
            selectedCheckpointIds: selectedCheckpoints,
          }),
        },
      );
    },
    onSuccess: (result) => {
      setGeneratedCount(result.generatedCount);
      void queryClient.invalidateQueries({ queryKey: ["test-cases"] });
    },
  });

  const acknowledge = useMutation({
    mutationFn: (caseId: string) =>
      apiFetch<TestCase>(`/test-cases/${caseId}/acknowledge-stale`, {
        method: "POST",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["test-cases"] });
    },
  });

  const removeCase = useMutation({
    mutationFn: (caseId: string) =>
      apiFetch<void>(`/test-cases/${caseId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["test-cases"] });
    },
  });

  const exportCases = useMutation({
    mutationFn: (format: "csv" | "markdown" | "json") =>
      apiFetchText(
        `/projects/${activeProjectId}/test-cases/export${queryString({ format })}`,
      ),
    onSuccess: setExportResult,
  });

  const canGeneratePlan = Boolean(activeProjectId && title.trim() && requirementText.trim() && modelId);
  const canGenerateCases = plan !== null && selectedCheckpoints.length > 0;

  return (
    <div className={styles.page} data-testid="case-library">
      <section className={styles.toolbar} aria-label="用例库工具栏">
        <FormField label="项目">
          <Select
            aria-label="项目"
            value={activeProjectId ? String(activeProjectId) : ""}
            placeholder="选择项目"
            options={(projectsQuery.data?.items ?? []).map((project) => ({
              value: String(project.projectId),
              label: project.name,
            }))}
            onChange={(value) => {
              setProjectId(value ? Number(value) : null);
              setExportResult(null);
            }}
          />
        </FormField>

        <dl className={styles.stats}>
          <div>
            <dt>总用例数</dt>
            <dd data-testid="total-count">{summary?.totalCount ?? 0}</dd>
          </div>
          <div>
            <dt>待复核数</dt>
            <dd data-testid="stale-count">{summary?.staleCount ?? 0}</dd>
          </div>
        </dl>

        <label className={styles.checkbox}>
          <input
            type="checkbox"
            checked={staleOnly}
            onChange={(event) => setStaleOnly(event.target.checked)}
          />
          只看待复核
        </label>

        <FormField label="优先级">
          <Select
            aria-label="优先级"
            value={priority}
            options={PRIORITY_OPTIONS}
            onChange={setPriority}
          />
        </FormField>

        <FormField label="关键词">
          <Input
            aria-label="关键词"
            placeholder="编号或标题"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
        </FormField>

        <div className={styles.actions}>
          {(["csv", "markdown", "json"] as const).map((format) => (
            <Button
              key={format}
              type="button"
              variant="secondary"
              loading={exportCases.isPending && exportCases.variables === format}
              onClick={() => exportCases.mutate(format)}
            >
              导出 {format === "markdown" ? "Markdown" : format.toUpperCase()}
            </Button>
          ))}
          <Button type="button" onClick={() => setGeneratorOpen((value) => !value)}>
            + 两阶段生成用例
          </Button>
        </div>
      </section>

      {generatorOpen ? (
        <section className={styles.panel} aria-label="两阶段生成用例">
          <header className={styles.panelHead}>
            <h2>两阶段生成用例</h2>
            <p className={styles.meta}>
              先推荐上下文，再生成检查点矩阵，勾选后才展开结构化用例。
            </p>
          </header>

          <div className={styles.inlineFields}>
            <FormField label="测试主题">
              <Input
                aria-label="测试主题"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </FormField>
            <FormField label="QA 技能">
              <Select
                aria-label="QA 技能"
                value={skillId}
                placeholder="使用内置规范"
                options={(skillsQuery.data?.items ?? []).map((skill) => ({
                  value: skill.skillId,
                  label: skill.name,
                }))}
                onChange={setSkillId}
              />
            </FormField>
            <FormField label="提供商">
              <Select
                aria-label="提供商"
                value={providerId}
                placeholder="选择提供商"
                options={(providersQuery.data?.items ?? []).map((provider) => ({
                  value: String(provider.providerId),
                  label: provider.name,
                }))}
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

          <FormField label="需求正文">
            <Textarea
              aria-label="需求正文"
              rows={5}
              value={requirementText}
              onChange={(event) => setRequirementText(event.target.value)}
            />
          </FormField>

          <div className={styles.actions}>
            <Button
              type="button"
              variant="secondary"
              loading={recommend.isPending}
              disabled={!title.trim() || !requirementText.trim()}
              onClick={() => recommend.mutate()}
            >
              智能推荐上下文
            </Button>
          </div>
          {recommend.isError ? (
            <ErrorState
              message={errorMessage(recommend.error, "上下文推荐失败")}
              retryable={false}
            />
          ) : null}

          {recommendation ? (
            <div className={styles.recommend}>
              <section aria-label="推荐知识条目">
                <h3>推荐知识条目</h3>
                {recommendation.recommendedKbEntries.length === 0 ? (
                  <p className={styles.meta}>没有匹配的知识条目。</p>
                ) : (
                  <ul className={styles.checkList}>
                    {recommendation.recommendedKbEntries.map((entry) => (
                      <li key={kbEntryKey(entry)}>
                        <label>
                          <input
                            type="checkbox"
                            checked={selectedKb.includes(kbEntryKey(entry))}
                            onChange={() =>
                              setSelectedKb((values) =>
                                toggle(values, kbEntryKey(entry)),
                              )
                            }
                          />
                          <code>{entry.code}</code> {entry.title}
                          <Badge
                            label={
                              MATCH_SOURCE_LABEL[entry.matchSource] ??
                              entry.matchSource
                            }
                            tone={entry.matchSource === "direct" ? "info" : "neutral"}
                          />
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section aria-label="推荐代码路径">
                <h3>推荐代码路径</h3>
                {recommendation.recommendedCodePaths.length === 0 ? (
                  <p className={styles.meta}>没有召回代码路径。</p>
                ) : (
                  <ul className={styles.checkList}>
                    {recommendation.recommendedCodePaths.map((item) => (
                      <li key={item.path}>
                        <label>
                          <input
                            type="checkbox"
                            checked={selectedPaths.includes(item.path)}
                            onChange={() =>
                              setSelectedPaths((values) =>
                                toggle(values, item.path),
                              )
                            }
                          />
                          <code>{item.path}</code>
                          <Badge
                            label={CODE_PATH_LABEL[item.source] ?? item.source}
                            tone="neutral"
                          />
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          ) : null}

          <div className={styles.actions}>
            <Button
              type="button"
              loading={createPlan.isPending}
              disabled={!canGeneratePlan}
              onClick={() => createPlan.mutate()}
            >
              生成检查点矩阵
            </Button>
          </div>
          {createPlan.isError ? (
            <ErrorState
              message={errorMessage(createPlan.error, "检查点矩阵生成失败")}
              retryable={false}
            />
          ) : null}

          {plan ? (
            <section className={styles.subsection} aria-label="检查点矩阵">
              <h3>阶段 1 · 检查点矩阵</h3>
              <ul className={styles.checkList}>
                {plan.checkpoints.map((checkpoint) => (
                  <li key={checkpoint.checkpointId}>
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedCheckpoints.includes(checkpoint.checkpointId)}
                        onChange={() =>
                          setSelectedCheckpoints((values) =>
                            toggle(values, checkpoint.checkpointId),
                          )
                        }
                      />
                      <code>{checkpoint.checkpointId}</code>
                      <span>{checkpoint.module}</span>
                      <span>{checkpoint.scenario}</span>
                      <Badge label={checkpoint.priority} tone="warning" />
                    </label>
                  </li>
                ))}
              </ul>
              <div className={styles.actions}>
                <Button
                  type="button"
                  loading={generate.isPending}
                  disabled={!canGenerateCases}
                  onClick={() => generate.mutate()}
                >
                  按勾选检查点生成用例
                </Button>
              </div>
              {generate.isError ? (
                <ErrorState
                  message={errorMessage(generate.error, "用例生成失败")}
                  retryable={false}
                />
              ) : null}
              {generatedCount !== null ? (
                <p role="status" className={styles.callout}>
                  阶段 2 完成，已生成 {generatedCount} 条结构化用例并写入用例库。
                </p>
              ) : null}
            </section>
          ) : null}
        </section>
      ) : null}

      <section className={styles.resultBar} aria-label="用例视图切换">
        <div role="group" aria-label="视图切换" className={styles.segmented}>
          <Button
            type="button"
            variant={view === "table" ? "primary" : "secondary"}
            aria-pressed={view === "table"}
            onClick={() => setView("table")}
          >
            表格视图
          </Button>
          <Button
            type="button"
            variant={view === "tree" ? "primary" : "secondary"}
            aria-pressed={view === "tree"}
            onClick={() => setView("tree")}
          >
            层级树视图
          </Button>
        </div>
      </section>

      {exportResult !== null ? (
        <section className={styles.exportPanel} aria-label="导出结果">
          <h3>导出结果</h3>
          <pre data-testid="export-result" className={styles.exportContent}>
            {exportResult}
          </pre>
        </section>
      ) : null}
      {exportCases.isError ? (
        <ErrorState
          message={errorMessage(exportCases.error, "导出失败")}
          retryable={false}
        />
      ) : null}

      {casesQuery.isPending ? (
        <Spinner label="加载用例库" />
      ) : casesQuery.isError ? (
        <ErrorState
          message="无法加载用例库"
          onRetry={() => void casesQuery.refetch()}
        />
      ) : cases.length === 0 ? (
        <EmptyState
          title="还没有测试用例"
          description="点击「+ 两阶段生成用例」，先推荐上下文再生成检查点矩阵。"
        />
      ) : view === "table" ? (
        <div data-testid="view-table" className={styles.tableCard}>
          <CaseTable
            cases={cases}
            expandedId={expandedId}
            onToggleSteps={(caseId) =>
              setExpandedId((current) => (current === caseId ? null : caseId))
            }
            onAcknowledge={(caseId) => acknowledge.mutate(caseId)}
            onDelete={(caseId) => removeCase.mutate(caseId)}
          />
        </div>
      ) : (
        <div data-testid="view-tree" className={styles.treeCard}>
          <ul className={styles.tree}>
            {(summary?.moduleTree ?? []).map((node) => (
              <TreeNode key={node.name} node={node} path="" cases={cases} />
            ))}
          </ul>
        </div>
      )}

      {acknowledge.isError ? (
        <ErrorState
          message={errorMessage(acknowledge.error, "确认复核失败")}
          retryable={false}
        />
      ) : null}
      {removeCase.isError ? (
        <ErrorState
          message={errorMessage(removeCase.error, "删除用例失败")}
          retryable={false}
        />
      ) : null}
    </div>
  );
}
