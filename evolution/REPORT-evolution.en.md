> English version. 中文原版：[REPORT-evolution.md](REPORT-evolution.md)

# Cross-version evolution of the Claude Code prompt (2.1.272 → 2.1.287)

> Method: run the same chunking pipeline over the artifacts of six versions installed on this machine, extract each **section body** (the template literal that contains the heading) and the **normalized prose lines**, then compare them.
> Normalization = strip `${}` interpolations, strip backticks, collapse whitespace; keep only long English sentences (≥60 characters, with no code symbols), to filter out minifier renaming noise.

## 1. Scale and cadence

| Version | Build date | Modules | Source characters | Prompt-like literals (≥120) |
|---|---|---|---|---|
| 2.1.272 | 09-15 | 1735 | 34,969,314 | 21,127 |
| 2.1.282 | 09-25 | 2071 | 39,247,181 | 23,403 |
| 2.1.283 | 09-27 | 2152 | 40,104,670 | 20,831 |
| 2.1.284 | 09-29 | 2166 | 40,746,649 | 23,322 |
| 2.1.286 | 10-02 | 2138 | 40,456,160 | 23,369 |
| 2.1.287 | 10-02 | 2173 | 41,177,656 | 24,826 |

## 2. Per-version status of the section bodies

(✓ = identical to 2.1.272; △N changes = N edits; similarity is the sequence similarity after normalization)

| Section | 2.1.272 | 2.1.282 | 2.1.283 | 2.1.284 | 2.1.286 | 2.1.287 |
|---|---|---|---|---|---|---|
| `# System` | ✓ | △6 changes/0.98 | △6 changes/0.98 | △7 changes/0.98 | △6 changes/0.99 | △6 changes/0.99 |
| `# Doing tasks` | ✓ | △3 changes/1.00 | △3 changes/1.00 | △3 changes/1.00 | △3 changes/1.00 | △3 changes/1.00 |
| `# Executing actions with care` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Using your tools` | ✓ | △4 changes/0.96 | △4 changes/0.96 | △4 changes/0.96 | △4 changes/0.96 | △4 changes/0.96 |
| `# Tone and style` | ✓ | △3 changes/0.99 | △3 changes/0.99 | △3 changes/0.99 | △3 changes/0.99 | △3 changes/0.99 |
| `# Harness` | ✓ | △3 changes/1.00 | △3 changes/1.00 | △3 changes/1.00 | △3 changes/1.00 | △3 changes/1.00 |
| `# Text output (does not apply to tool calls)` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Writing for the user` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Delivering work` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Corrections` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Context management` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Communicating with the user` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `# Environment` | ✓ | △6 changes/0.83 | △6 changes/0.83 | △6 changes/0.83 | △6 changes/0.83 | △6 changes/0.83 |

## 3. Real changes in section content relative to the earliest version

### `# System`
- **2.1.282**: 1189 → 1206 characters, similarity 0.984, 1 change
    - old: `ODo`
    - new: `...Xx()?[ZTe]:[],Q4n`
- **2.1.283**: 1189 → 1206 characters, similarity 0.984, 1 change
    - old: `ODo`
    - new: `...FP()?[yRe]:[],pXn`
- **2.1.284**: 1189 → 1206 characters, similarity 0.985, 1 change
    - old: `ODo`
    - new: `...XP()?[mxe]:[],SQn`
- **2.1.286**: 1189 → 1206 characters, similarity 0.985, 1 change
    - old: `OD`
    - new: `...sI()?[Bxe]:[],Kn`
- **2.1.287**: 1189 → 1206 characters, similarity 0.985, 1 change
    - old: `OD`
    - new: `...n0()?[bMe]:[],Ea`

### `# Harness`
- **2.1.282**: 527 → 529 characters, similarity 0.998, 1 change
    - new: `«»`
- **2.1.283**: 527 → 529 characters, similarity 0.998, 1 change
    - new: `«»`
- **2.1.284**: 527 → 529 characters, similarity 0.998, 1 change
    - new: `«»`
- **2.1.286**: 527 → 529 characters, similarity 0.998, 1 change
    - new: `«»`
- **2.1.287**: 527 → 529 characters, similarity 0.998, 1 change
    - new: `«»`

### `# Environment`
- **2.1.282**: 269 → 355 characters, similarity 0.827, 1 change
    - old: `t8`
    - new: `fxn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var jc`
- **2.1.283**: 269 → 355 characters, similarity 0.827, 1 change
    - old: `t8`
    - new: `uOn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var Ep`
- **2.1.284**: 269 → 355 characters, similarity 0.827, 1 change
    - old: `t8`
    - new: `bLn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var wp`
- **2.1.286**: 269 → 355 characters, similarity 0.827, 1 change
    - old: `t8`
    - new: `LFn="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var Tm`
- **2.1.287**: 269 → 355 characters, similarity 0.827, 1 change
    - old: `t8`
    - new: `S2n="Bash tool also available for POSIX scripts \u2014 each takes its own syntax";var wh`


## 4. Sentence-level additions and removals (adjacent versions, top 6 by length)

### 2.1.272 → 2.1.282
- Common 11,784 / added 3,434 / removed 2,028
    - added: HotUpdateEnabled,gJ as isFrameLiveSubscribeEnabled,hJ as isFrameLiveTokenLeaseEnabled,rR as isFrameMultiFileEnabled,Wb as isFramePublicReadEnabled,Clr
    - added: Requests the workspace git diff for the thin-client /diff dialog. The worker resolves one base ref for both stats and hunks (the merge-base with the b
    - added: G='**To update**: Edit the file, then call Artifact again with the same file path \u2014 it redeploys to the same URL. A different file path claims a 
    - added: ContentOriginUrlFor,KHr as artifactLeadScrubPattern,jAe as artifactLinkShapeHint,PLt as artifactLoginBlockedByCredentialMessage,NHr as artifactLoginEn
    - added: AgentTranscriptFetchError,FLo as ENTRY_APPEND_POLICY,ULo as INDEX_BOUNDARY_SCAN_BYTES,$Lo as INDEX_HEAD_SCAN_BYTES,BLo as INDEX_LAST_PROMPT_SCAN_BYTES
    - added: FreshnessWatcherStartedForTesting,HWo as _setGlobalConfigCacheForTesting,vWo as _setLastGetConfigWasParseErrorForTesting,OWo as _setLastReadFileStatsF
    - removed: CurrentSessionIsolationLatch,LXt as getCurrentSessionOffBoxPeerName,DXt as getCurrentSessionPeerName,nnt as getCurrentSessionPeerNameFor,Au as getCurr
    - removed: Xe as AuthenticationCancelledError,UXe as ClaudeAuthProvider,ED as IssuerEchoCrossOriginError,osr as McpClientRegistrationDeferredError,nsr as authori
    - removed: Won as artifactToolWithholdingGate,pMt as artifactYieldAdminRefusal,zon as getArtifactDefaultOn,gzr as holdArtifactStartupTelemetry,blt as isArtifactC
    - removed: Level:void 0,headMoved:void 0,workingCopyPath:void 0,settleFileChange:void 0,liveFileEnded:void 0,pushHeldSaves:void 0,heldSavesExitCleanup:void 0},au

### 2.1.282 → 2.1.283
- Common 13,735 / added 1,723 / removed 1,483
    - added: Source,WI as getRelativeSettingsFilePathForSource,Upt as getRuleAnchorRootForSource,_k as getSecuritySensitiveSetting,wne as getSecuritySensitiveSetti
    - added: Name,ZGo as getSubscriptionNameAsync,tr as getSubscriptionType,qFe as getSubscriptionTypeAsync,qun as getTurnOnUsageCreditsStep,PNt as getUnapprovedCu
    - added: Io as DefaultPolicyLimitsClientSlot,Z6o as FAIL_CLOSED_SHADOW_CACHE_TTL_MS,RGn as POLICY_LIMITS_COLD_AWAIT_MS,JKo as POLICY_LIMITS_FIRST_ATTEMPT_WAIT_
    - added: LateToolAdditionsOkEmitted,jmt as isLongContext1mCreditsBlocked,u3r as isMidConvCachePromotionRejected,a2t as isOTelInitPending,z6 as isOauthTokenFrom
    - added: FromType:new Map,deferredSurface:new Map,remoteControlSkippedSlugs:new Set,typeInstanceFiles:new Map,typeCatalogVouch:new Map,typeDescriptions:new Map
    - added: OAuthScope,h5o as hasOpusAccess,v5o as hasOpusAccessAsync,xp as hasProfileScope,b5o as hasProfileScopeAsync,MNr as hasStoredOAuthRefreshToken,rf as ha
    - removed: HotUpdateEnabled,gJ as isFrameLiveSubscribeEnabled,hJ as isFrameLiveTokenLeaseEnabled,rR as isFrameMultiFileEnabled,Wb as isFramePublicReadEnabled,Clr
    - removed: ContentOriginUrlFor,KHr as artifactLeadScrubPattern,jAe as artifactLinkShapeHint,PLt as artifactLoginBlockedByCredentialMessage,NHr as artifactLoginEn
    - removed: AgentTranscriptFetchError,FLo as ENTRY_APPEND_POLICY,ULo as INDEX_BOUNDARY_SCAN_BYTES,$Lo as INDEX_HEAD_SCAN_BYTES,BLo as INDEX_LAST_PROMPT_SCAN_BYTES
    - removed: FreshnessWatcherStartedForTesting,HWo as _setGlobalConfigCacheForTesting,vWo as _setLastGetConfigWasParseErrorForTesting,OWo as _setLastReadFileStatsF

### 2.1.283 → 2.1.284
- Common 14,011 / added 1,627 / removed 1,447
    - added: Code,iu as isExpectedApiError,Rt as isFsInaccessible,EC as isFsInaccessibleCode,f9r as isHttpServerConnReset,c2e as isNonRetryableClientError,u9r as i
    - added: Sync;pendingPluginRefresh;pluginRefreshJoined;mcpClientCountAtKick;mcpPrewaitPromise;firstCommandMountJoin;mcpPrewait;firstCommandTaken=!1;waitForPend
    - added: Claude Tag] Fixed Slack replies arriving many minutes late, or never, after Claude\'s session crashed mid-task, such as on a failed setup script; it n
    - added: CAr as awaitMemoryPrefetchBlocking,TAr as clearSentSkillNamesForAgent,SAr as conversationForDelta,bAr as conversationForSubagentDelta,on as createAtta
    - added: Turn}}class Yu{messageQueue;drain;prewaitLatch;turnOutcome;io;emit;stopping;messages;engine;drainSdkEvents;deferredToolUse;inTurnScope;onTurnStart;onF
    - added: AvailabilityStagesLogged,e2e as getChromeFlagOverride,Tqr as getCliSessionConfigCarried,oQn as getClientTruncatedAssistantIds,UWt as getClientType,wqr
    - removed: Source,WI as getRelativeSettingsFilePathForSource,Upt as getRuleAnchorRootForSource,_k as getSecuritySensitiveSetting,wne as getSecuritySensitiveSetti
    - removed: Name,ZGo as getSubscriptionNameAsync,tr as getSubscriptionType,qFe as getSubscriptionTypeAsync,qun as getTurnOnUsageCreditsStep,PNt as getUnapprovedCu
    - removed: Io as DefaultPolicyLimitsClientSlot,Z6o as FAIL_CLOSED_SHADOW_CACHE_TTL_MS,RGn as POLICY_LIMITS_COLD_AWAIT_MS,JKo as POLICY_LIMITS_FIRST_ATTEMPT_WAIT_
    - removed: LateToolAdditionsOkEmitted,jmt as isLongContext1mCreditsBlocked,u3r as isMidConvCachePromotionRejected,a2t as isOTelInitPending,z6 as isOauthTokenFrom

### 2.1.284 → 2.1.286
- Common 13,450 / added 2,375 / removed 2,188
    - added: Elses,UH as issuedUnderDepartedAccount,l9e as linkPathToSlug,PT as markAutoReactNoticePending,Mut as otherCommentPendingSeq,S6 as otherOrgClassifierMa
    - added: Improved artifact pages: Claude writes its design plan into the page instead of the reply, and uses the name you already gave something as the page ti
    - added: U0t as lockClaudeWorktree,hLe as mayReleaseWorktreeLock,MBn as parsePRReference,$Bn as passesCommitSafetyChecks,hV as persistWorktreeSession,N0t as re
    - added: KMt as SessionRecordsUnreadableError,jDr as admitDroppedIdsByDestination,BDr as admitReceiptForOutstandingSend,UDr as creditPacerForHeldSend,_zn as de
    - added: Fixed an approved Edit never going through when its target is a device, such as a file symlinked to /dev/null, and the approval came from the IDE diff
    - added: SidechainTranscript,qC as recordTranscript,ZBn as registerForeignConversationProbe,zrn as registerForeignTranscriptExitReStamp,ALe as registerLiveSupp
    - removed: Code,iu as isExpectedApiError,Rt as isFsInaccessible,EC as isFsInaccessibleCode,f9r as isHttpServerConnReset,c2e as isNonRetryableClientError,u9r as i
    - removed: Sync;pendingPluginRefresh;pluginRefreshJoined;mcpClientCountAtKick;mcpPrewaitPromise;firstCommandMountJoin;mcpPrewait;firstCommandTaken=!1;waitForPend
    - removed: Claude Tag] Fixed Slack replies arriving many minutes late, or never, after Claude\'s session crashed mid-task, such as on a failed setup script; it n
    - removed: CAr as awaitMemoryPrefetchBlocking,TAr as clearSentSkillNamesForAgent,SAr as conversationForDelta,bAr as conversationForSubagentDelta,on as createAtta

### 2.1.286 → 2.1.287
- Common 14,154 / added 2,073 / removed 1,671
    - added: DispatchableAgents,qu as findSafetyCheckReason,act as getDispatchableAgents,a4e as guardHookUpdatedInput,ict as hasAutoModeClassifierDenyRules,kf as h
    - added: HeldHipaaEvidence,l7n as getHipaaEvidence,lbe as getLastFetchOutcome,lzr as getLastPolicyCacheStampMatchedIdentity,rSn as getLastPolicyCacheStampVerdi
    - added: RegistryState,xc as isActingAsBgJob,p6t as isBeingWatched,f6t as isBeingWatchedV5,Pt as isBgSession,Boe as isDaemonBgWorker,SIe as isRegistrySweepPerm
    - added: AgentWorktreeChanges,Uc as getCurrentWorktreeSession,ZDt as getDefaultRemoteRef,u0r as getTmuxInstallInstructions,vGn as getWorkingCopyWorktreeChanges
    - added: MEe} You get no signal whether they saved it: report the skill as delivered, never as saved. Skill files on disk \u2014 including synced copies of the
    - added: Htt as appendSlackTagResumeRecords,xtt as computeStandaloneAgentContext,scr as exitRestoredWorktree,tve as installRestoredModel,rcr as lastTranscriptM
    - removed: Elses,UH as issuedUnderDepartedAccount,l9e as linkPathToSlug,PT as markAutoReactNoticePending,Mut as otherCommentPendingSeq,S6 as otherOrgClassifierMa
    - removed: Improved artifact pages: Claude writes its design plan into the page instead of the reply, and uses the name you already gave something as the page ti
    - removed: U0t as lockClaudeWorktree,hLe as mayReleaseWorktreeLock,MBn as parsePRReference,$Bn as passesCommitSafetyChecks,hV as persistWorktreeSession,N0t as re
    - removed: KMt as SessionRecordsUnreadableError,jDr as admitDroppedIdsByDestination,BDr as admitReceiptForOutstandingSend,UDr as creditPacerForHeldSend,_zn as de


## 5. Structural probes (whether constants/lists change across versions)

| Probe | 2.1.272 | 2.1.282 | 2.1.283 | 2.1.284 | 2.1.286 | 2.1.287 |
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

## 6. Conclusions

1. **The prompt body is essentially frozen across the six versions.** After normalization (stripping interpolations/backticks/collapsing whitespace), the seven sections `# Executing actions with care`, `# Text output`, `# Writing for the user`, `# Delivering work`, `# Corrections`, `# Context management`, and `# Communicating with the user` are **verbatim identical** between 2.1.272 and 2.1.287; `# Doing tasks` / `# Tone and style` / `# Harness` differ substantively in only 1 place each (a conditionally injected `${...}` fragment added), and `# System` has 1~2 differences of the same kind.
2. **Version growth happens in code and features, not in wording.** Source characters 34.97M → 41.18M (+18%), modules 1735 → 2173 (+25%), `tengu_*` flags 2,378 → 2,688 (+13%), yet the prompt skeleton does not move — which indicates that Anthropic treats the prompt as a **stable interface**, and carries new capabilities through new sections/tools/flags (added in this range: `## Clear, conversational English, with no Claude-isms`, `## Version control`, `## Calls served by an attached machine`, `## Phase 4 — Prune and index`, `# Claude Code gh stand-in shim`).
3. **The only clearly new subsystem is "memory"**: the `MEMORY.md` index constants (200 lines / 25,000 bytes) appear only in **2.1.287**, and the real request from 2.1.287 does indeed carry `# auto memory` with its 6 subsections (see [`../verify/REPORT-dynamic.en.md`](../verify/REPORT-dynamic.en.md)).
4. **Structural constants are highly stable**: 33 hook events, the todo reminder threshold `10/10`, the four built-in output style names, the three identity sentences, the dynamic boundary sentinel, and the billing header are all identical across the six versions.
5. A methodological reminder: diffing literals directly drowns in minifier renames (adjacent versions show tens of thousands of "added/removed" entries each), so interpolations must be normalized before comparing; even then, pure identifier renames still have to be filtered out (which is what this report does).

> Artifacts: `v2.1.2xx/prompts.jsonl` (literals per version), `v2.1.2xx/probes.json` (structural probes), `bundle-*.txt` (merged source text of each version, for re-inspection).
