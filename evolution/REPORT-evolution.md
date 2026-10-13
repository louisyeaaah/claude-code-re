# Claude Code 提示词跨版本演化（2.1.272 → 2.1.287）

> 方法：对六个本机安装版本的产物跑同一套切块，抽**小节正文**（取包含标题的那个模板字面量）与**归一化散文行**后对比。
> 归一化 = 去 `${}` 插值、去反引号、压缩空白；只保留英文长句（≥60 字符、无代码符号），以剔除 minifier 改名噪声。

## 1. 规模与节奏

| 版本 | 构建日期 | 模块数 | 源码字符 | 提示词型字面量(≥120) |
|---|---|---|---|---|
| 2.1.272 | 09-15 | 1735 | 34,969,314 | 21,127 |
| 2.1.282 | 09-25 | 2071 | 39,247,181 | 23,403 |
| 2.1.283 | 09-27 | 2152 | 40,104,670 | 20,831 |
| 2.1.284 | 09-29 | 2166 | 40,746,649 | 23,322 |
| 2.1.286 | 10-02 | 2138 | 40,456,160 | 23,369 |
| 2.1.287 | 10-02 | 2173 | 41,177,656 | 24,826 |

## 2. 小节正文的逐版本状态

（✓=与 2.1.272 完全一致；△N处=有 N 处改动；相似度为归一化后的序列相似度）

| 小节 | 2.1.272 | 2.1.282 | 2.1.283 | 2.1.284 | 2.1.286 | 2.1.287 |
|---|---|---|---|---|---|---|
| `# System` | ✓ | △6处/0.98 | △6处/0.98 | △7处/0.98 | △6处/0.99 | △6处/0.99 |
| `# Doing tasks` | ✓ | △3处/1.00 | △3处/1.00 | △3处/1.00 | △3处/1.00 | △3处/1.00 |
| `# Executing actions with care` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Using your tools` | ✓ | △4处/0.96 | △4处/0.96 | △4处/0.96 | △4处/0.96 | △4处/0.96 |
| `# Tone and style` | ✓ | △3处/0.99 | △3处/0.99 | △3处/0.99 | △3处/0.99 | △3处/0.99 |
| `# Harness` | ✓ | △3处/1.00 | △3处/1.00 | △3处/1.00 | △3处/1.00 | △3处/1.00 |
| `# Text output (does not apply to tool calls)` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Writing for the user` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Delivering work` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Corrections` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Context management` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Communicating with the user` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Environment` | ✓ | △6处/0.83 | △6处/0.83 | △6处/0.83 | △6处/0.83 | △6处/0.83 |

## 3. 小节内容相对最早版本的真实改动

### `# System`
- **2.1.282**：1189 → 1206 字符，相似度 0.984，1 处改动
    - 旧：`ODo`
    - 新：`...Xx()?[ZTe]:[],Q4n`
- **2.1.283**：1189 → 1206 字符，相似度 0.984，1 处改动
    - 旧：`ODo`
    - 新：`...FP()?[yRe]:[],pXn`
- **2.1.284**：1189 → 1206 字符，相似度 0.985，1 处改动
    - 旧：`ODo`
    - 新：`...XP()?[mxe]:[],SQn`
- **2.1.286**：1189 → 1206 字符，相似度 0.985，1 处改动
    - 旧：`OD`
    - 新：`...sI()?[Bxe]:[],Kn`
- **2.1.287**：1189 → 1206 字符，相似度 0.985，1 处改动
    - 旧：`OD`
    - 新：`...n0()?[bMe]:[],Ea`

### `# Harness`
- **2.1.282**：527 → 529 字符，相似度 0.998，1 处改动
    - 新：`«»`
- **2.1.283**：527 → 529 字符，相似度 0.998，1 处改动
    - 新：`«»`
- **2.1.284**：527 → 529 字符，相似度 0.998，1 处改动
    - 新：`«»`
- **2.1.286**：527 → 529 字符，相似度 0.998，1 处改动
    - 新：`«»`
- **2.1.287**：527 → 529 字符，相似度 0.998，1 处改动
    - 新：`«»`

### `# Environment`
- **2.1.282**：269 → 355 字符，相似度 0.827，1 处改动
    - 旧：`t8`
    - 新：`fxn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var jc`
- **2.1.283**：269 → 355 字符，相似度 0.827，1 处改动
    - 旧：`t8`
    - 新：`uOn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var Ep`
- **2.1.284**：269 → 355 字符，相似度 0.827，1 处改动
    - 旧：`t8`
    - 新：`bLn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var wp`
- **2.1.286**：269 → 355 字符，相似度 0.827，1 处改动
    - 旧：`t8`
    - 新：`LFn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var Tm`
- **2.1.287**：269 → 355 字符，相似度 0.827，1 处改动
    - 旧：`t8`
    - 新：`S2n="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var wh`


## 4. 整句级增删（相邻版本，按长度取前 6）

### 2.1.272 → 2.1.282
- 共有 11,784 / 新增 3,434 / 消失 2,028
    - 新增：HotUpdateEnabled,gJ as isFrameLiveSubscribeEnabled,hJ as isFrameLiveTokenLeaseEnabled,rR as isFrameMultiFileEnabled,Wb as isFramePublicReadEnabled,Clr
    - 新增：Requests the workspace git diff for the thin-client /diff dialog. The worker resolves one base ref for both stats and hunks (the merge-base with the b
    - 新增：G='**To update**: Edit the file, then call Artifact again with the same file path \u2014 it redeploys to the same URL. A different file path claims a 
    - 新增：ContentOriginUrlFor,KHr as artifactLeadScrubPattern,jAe as artifactLinkShapeHint,PLt as artifactLoginBlockedByCredentialMessage,NHr as artifactLoginEn
    - 新增：AgentTranscriptFetchError,FLo as ENTRY_APPEND_POLICY,ULo as INDEX_BOUNDARY_SCAN_BYTES,$Lo as INDEX_HEAD_SCAN_BYTES,BLo as INDEX_LAST_PROMPT_SCAN_BYTES
    - 新增：FreshnessWatcherStartedForTesting,HWo as _setGlobalConfigCacheForTesting,vWo as _setLastGetConfigWasParseErrorForTesting,OWo as _setLastReadFileStatsF
    - 消失：CurrentSessionIsolationLatch,LXt as getCurrentSessionOffBoxPeerName,DXt as getCurrentSessionPeerName,nnt as getCurrentSessionPeerNameFor,Au as getCurr
    - 消失：Xe as AuthenticationCancelledError,UXe as ClaudeAuthProvider,ED as IssuerEchoCrossOriginError,osr as McpClientRegistrationDeferredError,nsr as authori
    - 消失：Won as artifactToolWithholdingGate,pMt as artifactYieldAdminRefusal,zon as getArtifactDefaultOn,gzr as holdArtifactStartupTelemetry,blt as isArtifactC
    - 消失：Level:void 0,headMoved:void 0,workingCopyPath:void 0,settleFileChange:void 0,liveFileEnded:void 0,pushHeldSaves:void 0,heldSavesExitCleanup:void 0},au

### 2.1.282 → 2.1.283
- 共有 13,735 / 新增 1,723 / 消失 1,483
    - 新增：Source,WI as getRelativeSettingsFilePathForSource,Upt as getRuleAnchorRootForSource,_k as getSecuritySensitiveSetting,wne as getSecuritySensitiveSetti
    - 新增：Name,ZGo as getSubscriptionNameAsync,tr as getSubscriptionType,qFe as getSubscriptionTypeAsync,qun as getTurnOnUsageCreditsStep,PNt as getUnapprovedCu
    - 新增：Io as DefaultPolicyLimitsClientSlot,Z6o as FAIL_CLOSED_SHADOW_CACHE_TTL_MS,RGn as POLICY_LIMITS_COLD_AWAIT_MS,JKo as POLICY_LIMITS_FIRST_ATTEMPT_WAIT_
    - 新增：LateToolAdditionsOkEmitted,jmt as isLongContext1mCreditsBlocked,u3r as isMidConvCachePromotionRejected,a2t as isOTelInitPending,z6 as isOauthTokenFrom
    - 新增：FromType:new Map,deferredSurface:new Map,remoteControlSkippedSlugs:new Set,typeInstanceFiles:new Map,typeCatalogVouch:new Map,typeDescriptions:new Map
    - 新增：OAuthScope,h5o as hasOpusAccess,v5o as hasOpusAccessAsync,xp as hasProfileScope,b5o as hasProfileScopeAsync,MNr as hasStoredOAuthRefreshToken,rf as ha
    - 消失：HotUpdateEnabled,gJ as isFrameLiveSubscribeEnabled,hJ as isFrameLiveTokenLeaseEnabled,rR as isFrameMultiFileEnabled,Wb as isFramePublicReadEnabled,Clr
    - 消失：ContentOriginUrlFor,KHr as artifactLeadScrubPattern,jAe as artifactLinkShapeHint,PLt as artifactLoginBlockedByCredentialMessage,NHr as artifactLoginEn
    - 消失：AgentTranscriptFetchError,FLo as ENTRY_APPEND_POLICY,ULo as INDEX_BOUNDARY_SCAN_BYTES,$Lo as INDEX_HEAD_SCAN_BYTES,BLo as INDEX_LAST_PROMPT_SCAN_BYTES
    - 消失：FreshnessWatcherStartedForTesting,HWo as _setGlobalConfigCacheForTesting,vWo as _setLastGetConfigWasParseErrorForTesting,OWo as _setLastReadFileStatsF

### 2.1.283 → 2.1.284
- 共有 14,011 / 新增 1,627 / 消失 1,447
    - 新增：Code,iu as isExpectedApiError,Rt as isFsInaccessible,EC as isFsInaccessibleCode,f9r as isHttpServerConnReset,c2e as isNonRetryableClientError,u9r as i
    - 新增：Sync;pendingPluginRefresh;pluginRefreshJoined;mcpClientCountAtKick;mcpPrewaitPromise;firstCommandMountJoin;mcpPrewait;firstCommandTaken=!1;waitForPend
    - 新增：Claude Tag] Fixed Slack replies arriving many minutes late, or never, after Claude\'s session crashed mid-task, such as on a failed setup script; it n
    - 新增：CAr as awaitMemoryPrefetchBlocking,TAr as clearSentSkillNamesForAgent,SAr as conversationForDelta,bAr as conversationForSubagentDelta,on as createAtta
    - 新增：Turn}}class Yu{messageQueue;drain;prewaitLatch;turnOutcome;io;emit;stopping;messages;engine;drainSdkEvents;deferredToolUse;inTurnScope;onTurnStart;onF
    - 新增：AvailabilityStagesLogged,e2e as getChromeFlagOverride,Tqr as getCliSessionConfigCarried,oQn as getClientTruncatedAssistantIds,UWt as getClientType,wqr
    - 消失：Source,WI as getRelativeSettingsFilePathForSource,Upt as getRuleAnchorRootForSource,_k as getSecuritySensitiveSetting,wne as getSecuritySensitiveSetti
    - 消失：Name,ZGo as getSubscriptionNameAsync,tr as getSubscriptionType,qFe as getSubscriptionTypeAsync,qun as getTurnOnUsageCreditsStep,PNt as getUnapprovedCu
    - 消失：Io as DefaultPolicyLimitsClientSlot,Z6o as FAIL_CLOSED_SHADOW_CACHE_TTL_MS,RGn as POLICY_LIMITS_COLD_AWAIT_MS,JKo as POLICY_LIMITS_FIRST_ATTEMPT_WAIT_
    - 消失：LateToolAdditionsOkEmitted,jmt as isLongContext1mCreditsBlocked,u3r as isMidConvCachePromotionRejected,a2t as isOTelInitPending,z6 as isOauthTokenFrom

### 2.1.284 → 2.1.286
- 共有 13,450 / 新增 2,375 / 消失 2,188
    - 新增：Elses,UH as issuedUnderDepartedAccount,l9e as linkPathToSlug,PT as markAutoReactNoticePending,Mut as otherCommentPendingSeq,S6 as otherOrgClassifierMa
    - 新增：Improved artifact pages: Claude writes its design plan into the page instead of the reply, and uses the name you already gave something as the page ti
    - 新增：U0t as lockClaudeWorktree,hLe as mayReleaseWorktreeLock,MBn as parsePRReference,$Bn as passesCommitSafetyChecks,hV as persistWorktreeSession,N0t as re
    - 新增：KMt as SessionRecordsUnreadableError,jDr as admitDroppedIdsByDestination,BDr as admitReceiptForOutstandingSend,UDr as creditPacerForHeldSend,_zn as de
    - 新增：Fixed an approved Edit never going through when its target is a device, such as a file symlinked to /dev/null, and the approval came from the IDE diff
    - 新增：SidechainTranscript,qC as recordTranscript,ZBn as registerForeignConversationProbe,zrn as registerForeignTranscriptExitReStamp,ALe as registerLiveSupp
    - 消失：Code,iu as isExpectedApiError,Rt as isFsInaccessible,EC as isFsInaccessibleCode,f9r as isHttpServerConnReset,c2e as isNonRetryableClientError,u9r as i
    - 消失：Sync;pendingPluginRefresh;pluginRefreshJoined;mcpClientCountAtKick;mcpPrewaitPromise;firstCommandMountJoin;mcpPrewait;firstCommandTaken=!1;waitForPend
    - 消失：Claude Tag] Fixed Slack replies arriving many minutes late, or never, after Claude\'s session crashed mid-task, such as on a failed setup script; it n
    - 消失：CAr as awaitMemoryPrefetchBlocking,TAr as clearSentSkillNamesForAgent,SAr as conversationForDelta,bAr as conversationForSubagentDelta,on as createAtta

### 2.1.286 → 2.1.287
- 共有 14,154 / 新增 2,073 / 消失 1,671
    - 新增：DispatchableAgents,qu as findSafetyCheckReason,act as getDispatchableAgents,a4e as guardHookUpdatedInput,ict as hasAutoModeClassifierDenyRules,kf as h
    - 新增：HeldHipaaEvidence,l7n as getHipaaEvidence,lbe as getLastFetchOutcome,lzr as getLastPolicyCacheStampMatchedIdentity,rSn as getLastPolicyCacheStampVerdi
    - 新增：RegistryState,xc as isActingAsBgJob,p6t as isBeingWatched,f6t as isBeingWatchedV5,Pt as isBgSession,Boe as isDaemonBgWorker,SIe as isRegistrySweepPerm
    - 新增：AgentWorktreeChanges,Uc as getCurrentWorktreeSession,ZDt as getDefaultRemoteRef,u0r as getTmuxInstallInstructions,vGn as getWorkingCopyWorktreeChanges
    - 新增：MEe} You get no signal whether they saved it: report the skill as delivered, never as saved. Skill files on disk \u2014 including synced copies of the
    - 新增：Htt as appendSlackTagResumeRecords,xtt as computeStandaloneAgentContext,scr as exitRestoredWorktree,tve as installRestoredModel,rcr as lastTranscriptM
    - 消失：Elses,UH as issuedUnderDepartedAccount,l9e as linkPathToSlug,PT as markAutoReactNoticePending,Mut as otherCommentPendingSeq,S6 as otherOrgClassifierMa
    - 消失：Improved artifact pages: Claude writes its design plan into the page instead of the reply, and uses the name you already gave something as the page ti
    - 消失：U0t as lockClaudeWorktree,hLe as mayReleaseWorktreeLock,MBn as parsePRReference,$Bn as passesCommitSafetyChecks,hV as persistWorktreeSession,N0t as re
    - 消失：KMt as SessionRecordsUnreadableError,jDr as admitDroppedIdsByDestination,BDr as admitReceiptForOutstandingSend,UDr as creditPacerForHeldSend,_zn as de


## 5. 结构性探针（常量/清单是否随版本变化）

| 探针 | 2.1.272 | 2.1.282 | 2.1.283 | 2.1.284 | 2.1.286 | 2.1.287 |
|---|---|---|---|---|---|---|
| hook_event_count | 33 | 33 | 33 | 33 | 33 | 33 |
| todo_thresholds | ["TURNS_SINCE_WRITE:10,TURNS_BETWEEN | ["TURNS_SINCE_WRITE:10,TURNS_BETWEEN | ["TURNS_SINCE_WRITE:10,TURNS_BETWEEN | ["TURNS_SINCE_WRITE:10,TURNS_BETWEEN | ["TURNS_SINCE_WRITE:10,TURNS_BETWEEN | ["TURNS_SINCE_WRITE:10,TURNS_BETWEEN |
| memory_index_constants | [] | [] | [] | [] | [] | [["200", "25000"]] |
| output_styles | ["Concise", "Explanatory", "Learning | ["Concise", "Explanatory", "Learning | ["Concise", "Explanatory", "Learning | ["Concise", "Explanatory", "Learning | ["Concise", "Explanatory", "Learning | ["Concise", "Explanatory", "Learning |
| dynamic_boundary_sentinel | "yes" | "yes" | "yes" | "yes" | "yes" | "yes" |
| billing_header | "yes" | "yes" | "yes" | "yes" | "yes" | "yes" |
| skillify | true | true | true | true | true | true |
| doctor | true | true | true | true | true | true |
| dream_memory | true | true | true | true | true | true |
| workflow_authoring | true | true | true | true | true | true |
| coordinator_prompt | true | true | true | true | true | true |
| task_notification_xml | true | true | true | true | true | true |
| tengu_flag_calls_total | 2378 | 2594 | 2631 | 2667 | 2645 | 2688 |
| section_count | 17 | 17 | 18 | 18 | 18 | 18 |
| tool_count | 31 | 31 | 31 | 31 | 31 | 31 |

---

## 6. 结论

1. **提示词正文在六个版本间基本冻结。** 归一化（去插值/去反引号/压缩空白）后，`# Executing actions with care`、`# Text output`、`# Writing for the user`、`# Delivering work`、`# Corrections`、`# Context management`、`# Communicating with the user` 七个小节在 2.1.272→2.1.287 之间**逐字相同**；`# Doing tasks`/`# Tone and style`/`# Harness` 只有 1 处实质差异（新增一个条件注入的 `${...}` 片段），`# System` 有 1~2 处同类差异。
2. **版本增长发生在代码与功能，不在措辞。** 源码字符 3,497 万 → 4,118 万（+18%）、模块 1735 → 2173（+25%）、`tengu_*` 开关 2,378 → 2,688（+13%），但提示词骨架不动——说明 Anthropic 把提示词当**稳定接口**，新能力靠新小节/新工具/新开关承载（本区间新增：`## Clear, conversational English, with no Claude-isms`、`## Version control`、`## Calls served by an attached machine`、`## Phase 4 — Prune and index`、`# Claude Code gh stand-in shim`）。
3. **唯一明显新增的子系统是「记忆」**：`MEMORY.md` 索引常量（200 行 / 25,000 字节）只在 **2.1.287** 出现，而 2.1.287 的真实请求里也确实带上了 `# auto memory` 及其 6 个子节（见 [`../verify/REPORT-dynamic.md`](../verify/REPORT-dynamic.md)）。
4. **结构性常量高度稳定**：hook 事件 33 个、todo 提醒阈值 `10/10`、输出风格四个内置名、身份三句话、动态边界哨兵、计费头，六个版本全一致。
5. 方法学提醒：直接 diff 字面量会被 minifier 改名淹没（相邻版本"新增/删除"各上万条），必须归一化插值后再比；即便如此，仍要剔除纯标识符改名（本报告的做法）。

> 产物：`v2.1.2xx/prompts.jsonl`（各版字面量）、`v2.1.2xx/probes.json`（结构探针）、`bundle-*.txt`（各版源码合并文本，供复查）。
