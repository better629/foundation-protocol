# FP 架构设计（统一版）

Status: Proposed  
Date: 2026-03-01

## 1. 目标与使命

FP 是面向智能体社会的基础控制平面，其使命是让异构实体在开放环境中能够：

1. 低成本互联与协作。
2. 可解释地组织与治理。
3. 可验证地交换价值。
4. 可追溯地满足安全与合规。

该架构追求“核心小而稳、扩展快而灵活”。

---

## 2. 核心设计约束

1. **Graph-first**：实体是节点，关系与成员关系是边，交互是图上的活动。
2. **Multi-party by default**：多人协作是默认形态，不是例外分支。
3. **Progressive disclosure**：先交换轻量摘要，再按授权拉取详情。
4. **Evidence-first**：策略、溯源、审计是协议常规输出，不是外部日志补丁。
5. **Profile-oriented evolution**：可变项进入 profile/extension，核心语义保持稳定。

---

## 3. 4+1 架构平面

FP 采用四个核心平面 + 一个配置平面：

1. **Entity & Trust Plane**
2. **Transport & Routing Plane**
3. **Interaction & Organization Plane**
4. **Regulation & Oversight Plane**
5. **Configuration & Profiles Plane**

平面边界原则：

1. 核心平面只定义跨域必须互操作的语义。
2. 具体传输、身份机制、行业模式由 profile 绑定。
3. 扩展不破坏核心对象和核心状态机。

---

## 4. 代码架构（`fp` 包）

```text
fp/
  __init__.py

  # L1: 最简接入
  quickstart/
    agent.py
    tool.py
    resource.py
    client.py
    service.py

  # L2: 应用层 API
  app/
    server.py
    client.py
    decorators.py
    middleware.py

  # L3: 协议契约
  protocol/
    models.py
    methods.py
    envelope.py
    errors.py
    normalize.py

  # 图与组织语义
  graph/
    entities.py
    memberships.py
    organizations.py
    relations.py

  # Runtime 内核
  runtime/
    session_engine.py
    activity_engine.py
    event_engine.py
    dispatch_engine.py
    backpressure.py
    idempotency.py

  # 经济原语
  economy/
    meter.py
    receipt.py
    settlement.py
    dispute.py

  # 框架接入抽象
  adapters/
    base.py
    registry.py
    helpers.py

  # 传输
  transport/
    inproc.py
    stdio.py
    http_jsonrpc.py
    sse.py
    websocket.py

  # 存储
  stores/
    interfaces.py
    memory.py
    sqlite.py
    redis.py

  # 治理与安全
  policy/
    hooks.py
    decision.py
  security/
    auth.py
    authz.py
    signatures.py

  # 可观测与成本
  observability/
    trace.py
    metrics.py
    token_meter.py
    cost_meter.py
    audit_export.py

  # Profile 与扩展注册
  profiles/
    core_minimal.py
    core_streaming.py
    governed.py
  registry/
    schemas.py
    event_types.py
    patterns.py
```

分层约束：

1. `runtime` 不依赖具体 Agent 框架。
2. `adapters` 只依赖 `runtime + protocol`。
3. `quickstart` 只做组装，不承载复杂业务逻辑。
4. `economy/policy/observability` 可插拔，但输出语义必须一致。

---

## 5. 编程模型（对开发者）

FP 提供三层 API：

1. `quickstart API`：最快接入（默认入口）。
2. `application API`：定制中间件、存储、治理与运维。
3. `protocol API`：完整协议控制与底层调优。

推荐入口：

1. `from fp.quickstart import Agent, ToolNode, ResourceNode`
2. `from fp.app import FPServer, FPClient`

---

## 6. Runtime 内核

## 6.1 核心组件

1. `SessionEngine`：握手、版本协商、会话上下文。
2. `ActivityEngine`：活动状态机与状态跳转约束。
3. `EventEngine`：事件发布、流式分发、ACK、重放。
4. `DispatchEngine`：将请求路由到本地 handler 或 adapter。
5. `BackpressureController`：窗口控制、速率限制、拥塞保护。
6. `IdempotencyGuard`：写操作去重，确保重试安全。

## 6.2 统一生命周期

1. `activities.start`：创建 activity，进入 `submitted/working`。
2. `activities.update`：推进状态与中间产物。
3. `events.stream`：消费事件流。
4. `events.resubscribe`：断线续传。
5. `events.ack`：确认消费游标并回收缓存。
6. `activities.result`：读取最终结果元信息。
7. `activities.cancel`：取消执行并生成取消事件。

---

## 7. 图模型与组织语义

## 7.1 图对象

1. `Entity`：可寻址参与方。
2. `Relationship`：实体关系边。
3. `Membership`：组织成员边（带角色与委托约束）。
4. `Session`：多方协作容器边集。
5. `Activity`：图上的可观察交互单元。

## 7.2 多方协作默认化

1. 所有 activity 必须可关联 session。
2. session 必须可表达 participants/roles/policy_ref/budget。
3. 高风险动作可要求显式审批角色。

---

## 8. 不同实体如何使用 FP

## 8.1 LLM（模型能力提供者）

LLM 最自然角色是 `Tool Provider`：

1. 暴露 `invoke` 能力，例如 `llm.generate`。
2. 输入传结构化参数或 `prompt_ref`。
3. 输出传 `result_ref + usage`，避免大文本内联。

```python
from fp.quickstart import ToolNode

llm = ToolNode(entity_id="fp:tool:llm")

@llm.invoke("llm.generate")
async def generate(prompt_ref: str, model: str) -> dict:
    return {
        "result_ref": "obj://results/r-123",
        "usage": {"input_tokens": 320, "output_tokens": 140},
    }

llm.serve_http("0.0.0.0", 8088)
```

## 8.2 通用 Agent 框架

任何框架都可通过 Adapter 接入：

1. run/thread -> `session`
2. task/job -> `activity`
3. step/status callback -> `event`
4. cancel token -> `activities.cancel`
5. output/artifact -> `activities.result`（`result_ref`）

## 8.3 执行动作系统（UI/桌面/浏览器自动化等）

1. 每个动作映射为 `invoke` 或 activity 子步骤。
2. 每步都产出事件（started/progress/completed/failed）。
3. 长流程统一进同一 trace 和 session。

## 8.4 组织与治理实体

1. 成员与角色变更事件化。
2. 委托和预算约束协议化。
3. 治理策略与审计证据可独立验证。

---

## 9. Adapter 抽象（框架无关）

任何框架最小实现 L0 即可接入：

1. `start_activity`
2. `cancel_activity`
3. `poll_updates`
4. `fetch_result`
5. `error_mapping`

参考接口：

```python
class FrameworkAdapter(Protocol):
    async def start_activity(self, ctx, req) -> "AdapterStartResult": ...
    async def cancel_activity(self, ctx, activity_id: str) -> "AdapterCancelResult": ...
    async def poll_updates(self, ctx, activity_id: str) -> list["AdapterEvent"]: ...
    async def fetch_result(self, ctx, activity_id: str) -> "AdapterResult": ...
```

完成 L0 后自动获得：

1. 统一流式与断线恢复。
2. 统一状态机与错误码。
3. 统一观测、计量与治理挂点。

---

## 10. 经济原语实现

FP 经济层不绑定具体货币与账本，但统一四类对象：

1. `MeterRecord`：计量（token/ms/byte/call/custom）。
2. `Receipt`：可验证交付凭证。
3. `Settlement`：结算引用与状态。
4. `Dispute`：争议、撤销、升级信号。

实现要求：

1. 计量与活动、实体、策略可关联。
2. receipt 可独立校验（签名/哈希）。
3. settlement 可引用外部支付或清算系统。
4. dispute 可绑定证据引用并进入审计链路。

---

## 11. 治理、溯源与审计主干

## 11.1 治理挂点

1. `PRE_INVOKE`：鉴权、授权、策略预检。
2. `PRE_ROLE_CHANGE`：组织权限变更预检。
3. `PRE_SETTLE`：结算前策略检查。
4. `POST_EVENT_AUDIT`：关键事件审计。

## 11.2 证据主干

1. 每个策略决策都有 `decision_id`。
2. provenance 可回溯到 session/activity/event。
3. 敏感原文默认不入控制面，仅保留摘要与引用。
4. 审计导出可在不同策略视角下复核同一执行痕迹。

---

## 12. Token Efficient 与低延迟设计

## 12.1 协议侧优化（默认开启）

1. `progressive disclosure`：只发能力摘要，详情按需拉取。
2. `entity_card_hash`：无变化不重复发送 card。
3. `session default inheritance`：重复字段会话级继承。
4. `delta events`：事件默认增量而非全量。
5. `ref-first payload`：大内容统一走 `*_ref`。

## 12.2 Runtime 优化（默认开启）

1. inproc 零拷贝通道优先。
2. 流式 10~30ms 微批 flush（可配置）。
3. EventStore 与网络发送解耦，慢消费者不阻塞主流程。
4. ACK 窗口背压，拒绝无限缓冲。
5. 治理快速失败，避免无效执行成本。

## 12.3 性能预算（SLO）

1. `initialize` 协议增量开销 <= 1.5KB。
2. 普通 `invoke` 协议壳开销 <= 300B。
3. 状态流事件平均 <= 220B（delta）。
4. 控制面额外延迟 p95：inproc <= 5ms，HTTP+SSE <= 15ms。

---

## 13. 存储与一致性

最小存储抽象：

1. `SessionStore`
2. `ActivityStore`
3. `EventStore`
4. `ReceiptStore`
5. `ProvenanceStore`

一致性语义：

1. 事件投递 at-least-once。
2. 客户端依赖 `event_id + ack` 幂等消费。
3. 写请求通过 `idempotency_key` 去重。
4. 不追求全局 exactly-once。

---

## 14. 部署拓扑

## 14.1 单机模式

1. runtime + memory store + SSE。
2. 用于本地开发和集成测试。

## 14.2 服务化模式

1. runtime 无状态多副本。
2. Redis/Postgres 承载会话与事件。
3. 网关负责认证、限流、流量治理。

## 14.3 中心化控制平面模式

1. FP Runtime 作为统一控制中心。
2. 多个异构框架通过 adapter 接入。
3. 对外暴露统一 FP API。

---

## 15. 实施路线

## Phase A: Core Runtime

1. `SessionEngine/ActivityEngine/EventEngine`。
2. 内存存储 + 基本流式。
3. L0 Adapter + MockAdapter。

## Phase B: Adapter SDK

1. `BaseAdapter` 与 hook helpers。
2. 至少一个真实框架适配器。
3. adapter conformance suite。

## Phase C: Production

1. Redis/Postgres 存储实现。
2. policy/provenance/receipt/settlement/dispute 全链路。
3. 性能与成本基线稳定化。

---

## 16. 成功标准

当以下条件满足时，FP 架构达成目标：

1. 新框架可在一天内完成 L0 接入。
2. 长任务在断线后可稳定恢复。
3. 单位任务 token 与延迟开销可测、可控、可回归。
4. 治理和审计不依赖业务自定义日志。
5. 计量、凭证、结算、争议可在外部独立复核。
