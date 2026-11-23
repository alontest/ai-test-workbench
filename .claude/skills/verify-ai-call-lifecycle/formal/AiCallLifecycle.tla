---------------------------- MODULE AiCallLifecycle ----------------------------
\* 模型对象：src/vigil_workbench/services/ai_gateway.py 的 AiGateway.complete
\* 加 src/vigil_workbench/startup.py 的 merge_running_calls（进程重启时的 running 归并）。
\*
\* 每个常量/变量到代码的对应：
\*   record[c] = "none"        调用尚未写入 ai_call_record
\*   record[c] = "running"     ai_call_record.status = 'running' 已提交
\*   record[c] = "success"     终结为 success（同一事务追加 call 事件）
\*   record[c] = "failed"      终结为 failed
\*   record[c] = "timeout"     终结为 timeout
\*   record[c] = "interrupted" 终结为 failed(interrupted)
\*   active                    已插入 running、尚未终结的调用数（受 ai_max_concurrency 限制）
\*   callEvents[c]             已提交的 session_event(type="call") 条数
\*   done[c]                   complete() 这个协程已经结束（返回、抛错或被取消）
\*   restarted                 至少跑过一次启动自检的归并
\*
\* 范围声明：只建模单进程、单会话、call 事件的提交时机；不建模 knowledge_injection
\* 事件、重试次数、数据库提交的半途失败。
EXTENDS Naturals, TLC

CONSTANTS
    Calls,           \* 并发发起的调用集合
    MaxConcurrency   \* VIGIL_AI_MAX_CONCURRENCY

None == "none"
Running == "running"
Succeeded == "success"
Failed == "failed"
Timeout == "timeout"
Interrupted == "interrupted"

Terminal == {Succeeded, Failed, Timeout, Interrupted}

VARIABLES record, active, callEvents, done, restarted

vars == <<record, active, callEvents, done, restarted>>

TypeOK ==
    /\ record \in [Calls -> {None, Running, Succeeded, Failed, Timeout, Interrupted}]
    /\ active \in 0..MaxConcurrency
    /\ callEvents \in [Calls -> 0..1]
    /\ done \in [Calls -> BOOLEAN]
    /\ restarted \in BOOLEAN

Init ==
    /\ record = [c \in Calls |-> None]
    /\ active = 0
    /\ callEvents = [c \in Calls |-> 0]
    /\ done = [c \in Calls |-> FALSE]
    /\ restarted = FALSE

\* async with self._get_semaphore(): record_id = await self._insert_running(...)
Insert(c) ==
    /\ record[c] = None
    /\ ~done[c]
    /\ active < MaxConcurrency
    /\ record' = [record EXCEPT ![c] = Running]
    /\ active' = active + 1
    /\ UNCHANGED <<callEvents, done, restarted>>

\* _finalize(status in {success, failed, timeout})：同事务写记录并追加一条 call 事件
Finalize(c, outcome) ==
    /\ outcome \in {Succeeded, Failed, Timeout}
    /\ record[c] = Running
    /\ ~done[c]
    /\ record' = [record EXCEPT ![c] = outcome]
    /\ callEvents' = [callEvents EXCEPT ![c] = callEvents[c] + 1]
    /\ done' = [done EXCEPT ![c] = TRUE]
    /\ active' = active - 1
    /\ UNCHANGED restarted

\* 取消落在受保护的 try 里：except CancelledError 立刻终结为 failed(interrupted)
CancelFinalized(c) ==
    /\ record[c] = Running
    /\ ~done[c]
    /\ record' = [record EXCEPT ![c] = Interrupted]
    /\ callEvents' = [callEvents EXCEPT ![c] = callEvents[c] + 1]
    /\ done' = [done EXCEPT ![c] = TRUE]
    /\ active' = active - 1
    /\ UNCHANGED restarted

\* 取消落在 try 之外：running 记录已提交，但没有任何 except/finally 覆盖这个窗口。
\* 覆盖的两个真实窗口：
\*   a) _insert_running 已提交、还没进入 try（await db.commit() / 会话关闭 / 信号量退出）
\*   b) 成功分支的 await self._finalize(...) 本身被取消（它在 try 之外）
CancelUnhandled(c) ==
    /\ record[c] = Running
    /\ ~done[c]
    /\ done' = [done EXCEPT ![c] = TRUE]
    /\ active' = active - 1
    /\ UNCHANGED <<record, callEvents, restarted>>

\* 取消发生在拿到信号量、running 记录提交之前：没有记录，也没有事件
CancelBeforeInsert(c) ==
    /\ record[c] = None
    /\ ~done[c]
    /\ done' = [done EXCEPT ![c] = TRUE]
    /\ UNCHANGED <<record, active, callEvents, restarted>>

\* 进程崩溃后下一次启动：startup.py 的 merge_running_calls 把 running 归并为
\* failed(interrupted)，同一事务追加 call 事件；进程内所有协程都已消失。
Restart ==
    /\ \E c \in Calls: ~done[c] \/ record[c] = Running
    /\ record' = [c \in Calls |->
            IF record[c] = Running THEN Interrupted ELSE record[c]]
    /\ callEvents' = [c \in Calls |->
            IF record[c] = Running THEN callEvents[c] + 1 ELSE callEvents[c]]
    /\ done' = [c \in Calls |-> TRUE]
    /\ active' = 0
    /\ restarted' = TRUE

Next ==
    \/ \E c \in Calls: Insert(c)
    \/ \E c \in Calls, outcome \in {Succeeded, Failed, Timeout}: Finalize(c, outcome)
    \/ \E c \in Calls: CancelFinalized(c)
    \/ \E c \in Calls: CancelUnhandled(c)
    \/ \E c \in Calls: CancelBeforeInsert(c)
    \/ Restart

Spec == Init /\ [][Next]_vars

\* 上游并发不超过 VIGIL_AI_MAX_CONCURRENCY
ConcurrencyBound == active <= MaxConcurrency

\* 一次调用最多一条 call 事件（重启归并与取消终结不会重复追加）
CallEventAtMostOnce == \A c \in Calls: callEvents[c] <= 1

\* 已写入终态的记录恰好有一条 call 事件
EventMatchesRecord ==
    \A c \in Calls: record[c] \in Terminal => callEvents[c] = 1

\* 核心承诺：所有协程都结束后，任何记录都不再是 running。
\* 反例即「用户会看到一个永远转圈的调用」。
SettledWhenAllDone ==
    (\A c \in Calls: done[c]) => (\A c \in Calls: record[c] # Running)

====
