# Architecture

See [`ARCHITECTURE.html`](ARCHITECTURE.html) for the rendered diagrammed version.

## Layered diagram (Mermaid)

```mermaid
flowchart LR
    subgraph Ingest[Data Ingestion]
      CSV[CSV uploads]
      API_IN[/api/v1/data/ingest/]
    end
    subgraph Process[Data Processing]
      Norm[Normalize]
      Feat[Features]
    end
    subgraph Pred[Predictive ML]
      F[Forecast · sn/ema/gbm]
      S[Stockout]
      A[Anomaly]
      SR[Supplier Risk]
    end
    subgraph Exc[Exception Engine]
      Det[Detect + Score]
    end
    subgraph Events[Event Bus]
      OB[Outbox + In-Proc Broker]
    end
    subgraph Agents[LangGraph-equivalent Supervisor]
      Sup[Supervisor]
      D[Demand]
      I[Inventory]
      Sp[Supplier]
      Al[Alt Sourcing]
      Bi[Business Impact]
    end
    subgraph Decide[Decision Intelligence]
      R[Recommendations]
      Sim[Simulator]
    end
    subgraph HITL[Governance]
      Ap[Approvals]
      Act[Simulated Action Adapter]
    end

    CSV --> Norm
    API_IN --> Norm
    Norm --> Feat
    Feat --> F
    Feat --> S
    Feat --> A
    Feat --> SR
    F --> Det
    S --> Det
    A --> Det
    SR --> Det
    Det --> OB
    OB --> Sup
    Sup --> D
    Sup --> I
    Sup --> Sp
    Sup --> Al
    D --> Bi
    I --> Bi
    Sp --> Bi
    Al --> Bi
    Bi --> R
    R --> Ap
    Sim --> R
    Ap --> Act
    Act --> OB
```

## LangGraph-equivalent orchestrator

```mermaid
stateDiagram-v2
    [*] --> Supervisor
    Supervisor --> Demand : if demand/stockout category
    Supervisor --> Inventory : if stockout/excess/aging
    Supervisor --> Supplier : if supplier/regional
    Demand --> BusinessImpact
    Inventory --> AltSourcing
    Supplier --> AltSourcing
    AltSourcing --> BusinessImpact
    BusinessImpact --> AggregateRank
    AggregateRank --> HumanApprovalInterrupt
    HumanApprovalInterrupt --> [*]
```

## Event flow

```mermaid
sequenceDiagram
    participant Eng as Exception Engine
    participant Out as Outbox
    participant Bus as Broker
    participant Sup as Supervisor
    participant Act as Action Adapter
    Eng->>Out: insert StockoutRiskDetected
    Out->>Bus: dispatch (idempotent)
    Bus->>Sup: deliver event
    Sup->>Sup: run specialists
    Sup->>Out: insert RecommendationGenerated
    Note over Act: Human approves → execute() emits ActionExecuted
```

---
*Author: **Pradeep Sahoo**.*
