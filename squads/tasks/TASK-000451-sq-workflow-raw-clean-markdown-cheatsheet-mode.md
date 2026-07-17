---
id: TASK-451
sequence_id: 451
type: task
title: sq workflow --raw clean-markdown cheatsheet mode
status: Done
parent: FEAT-449
author: tech-lead
assignee: python-dev
refs:
- ADR-427:addresses
description: 'Core: clean-markdown workflow cheatsheet, no Rich chrome (US4/F8 core
  half)'
created_at: '2026-07-17T13:23:45Z'
updated_at: '2026-07-17T14:14:16Z'
---
<!-- sq:body -->
Story: US4 (workflow cheatsheet view). Covers REV-448 finding F8 — the **core half** only; the client title button is a dependent task.

## Problem

`sq workflow` / `sq workflow show` renders the cheatsheet through `rich.Markdown` + Rich `Table`, emitting terminal chrome (box-drawing characters, ANSI) — unusable as markdown piped into a VS Code preview. This is the same gap `sq show` had before `--raw` landed.

## Scope

Add a clean-markdown mode — `sq workflow --raw` (and `sq workflow show --raw`) — that emits genuine markdown: markdown tables plus fenced ```mermaid blocks, no box-drawing, no Rich panels, no ANSI. Reuse the existing `workflow.md.j2` partial (it already backs both the `squads` skill and the Rich cheatsheet); the raw mode prints the rendered markdown source directly instead of piping it through `rich.Markdown`. Put `--raw` on both the bare `sq workflow` callback and the `show` sub-command for parity with how the Rich path is reached.

Mirror the `sq show --raw` precedent (opt out of the markdown render, plain text out).

## Requirements

- Output is ANSI-clean and box-drawing-free (verify no escape codes even under `FORCE_COLOR`).
- Diagrams emit as fenced ```mermaid blocks (the client's built-in-preview caveat is handled client-side).
- Golden-frozen: new golden (e.g. `workflow_cheatsheet_raw.txt`) with a test.
- Reviewer-gated (independent review before merge).

## Acceptance

- `sq workflow --raw` and `sq workflow show --raw` print clean markdown: markdown tables, fenced mermaid, zero box-drawing chars, no ANSI.
- Golden committed + assertion.
- Full Python suite + `pyright` strict + `ruff` green; `sq check` clean.
- CHANGELOG note.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 451 add-subtask "<title>"`; track with `sq task 451 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:04:58Z] Elias Python:
  - Added --raw to both the bare Team workflow                                                                   
    
     • Items are addressed as sq <type> <number> <verb> (e.g. sq task 35 show);     
       create with sq create <type>. Run sq <type> --help / sq <type> <n> --help to 
       explore.                                                                     
     • Product owner → sq create epic "…" --author product-owner.                   
     • Product owner → sq create feature "…" --author product-owner, then add-story 
       "…".                                                                         
     • Tech lead → sq create task "…" --author tech-lead --parent FEAT-…, then      
       add-subtask "…" --story USn; link with ref add <id> --kind fixes|addresses.  
     • QA engineer → sq create bug "…" --author qa.                                 
     • Architect → sq create decision "…" --author architect; link with ref add <id>
       --kind supersedes.                                                           
     • Code reviewer → sq create review "…" --author reviewer, then add-finding "…".
     • Sub-entities are tracked too: feature → story (Todo → InProgress → Done (+   
       Blocked, Cancelled)); task → subtask (Todo → InProgress → Done (+ Blocked,   
       Cancelled)); review → finding (Open → Fixed → Verified (+ WontFix)). update  
       is the one metadata entry point for a sub-entity                             
       (--title/--status/--assignee, plus any declared field flag). Each parent     
       shows an sq-managed summary table.                                           
     • Hierarchy: epic → feature → task. sq check enforces the parent rules.        
     • Each role has skills for the item types it manages (e.g. sq-epic, sq-feature,
       sq-task, …) — open those for role-specific guidance. The default role triages
       and routes when no other agent claims the work.                              
     • The .md files are sq-managed — never hand-edit them. Set an item's body with 
       sq <type> <n> body -m "…" (or --file); a sub-entity's with sq <type> <n>     
       <kind> <k> body -m "…"; read back with sq <type> <n> show --full --comments  
       (full dossier). Hand off with sq <type> <n> comment --as <slug> -m "…"       
       (repeat -m for separate bullets; use @role).                                 
    
    Item hierarchy                                                                  
    
                                                                                    
     flowchart TD                                                                   
         epic["epic"] --> feature["feature"]                                        
         feature["feature"] --> task["task"]                                        
                                                                                    
    
    Type-command aliases                                                            
    
    Short and single-letter aliases for the item-type commands — input sugar only.  
    They are hidden from root --help but fully equivalent: every alias accepts      
    everything the canonical name does, including sub-entity chains (sq f 26 story 4
    show). Output (IDs, errors, --json) always uses the canonical type name. Run sq 
    workflow to see this table in the terminal.                                     
    
                                       
     Canonical  Aliases  Example       
     ───────────────────────────────── 
     epic       e        sq e <n> show 
     feature    feat, f  sq f <n> show 
     task       t        sq t <n> show 
     bug        b        sq b <n> show 
     decision   dec, d   sq d <n> show 
     review     rev, r   sq r <n> show 
     guide      g        sq g <n> show 
                                       
    
    Evolution rule (stability contract): adding an alias is additive and allowed;   
    removing or repurposing an alias is a breaking change and is not permitted after
    1.0. The alias table is frozen grammar in the same stability tier as the        
    canonical command names.                                                        
    
    Type lifecycles                                                                 
    
    Lifecycle strings auto-derived from each type's state machine — the source of   
    truth for valid statuses and transitions.                                       
    
                                                                                    
     Prefix  Type      Lifecycle                                                    
     ────────────────────────────────────────────────────────────────────────────── 
     EPIC    epic      Draft → Ready → InProgress → InReview → Done (+ Blocked,     
                       Cancelled)                                                   
     FEAT    feature   Draft → Ready → InProgress → InReview → Done (+ Blocked,     
                       Cancelled)                                                   
     TASK    task      Draft → Ready → InProgress → InReview → Done (+ Blocked,     
                       Cancelled)                                                   
     BUG     bug       Open → InProgress → Fixed → Verified (+ WontFix, Blocked,    
                       Cancelled)                                                   
     ADR     decision  Proposed → Accepted → Superseded (+ Rejected, Deprecated)    
     REV     review    Requested → InReview → ChangesRequested → Approved (+        
                       Rejected)                                                    
     GUIDE   guide     Draft → Published → Deprecated                               
                                                                                    
    
    epic lifecycle:                                                                 
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Draft                                                              
         Draft : Draft                                                              
         Ready : Ready                                                              
         InProgress : InProgress                                                    
         Cancelled : Cancelled                                                      
         Blocked : Blocked                                                          
         InReview : InReview                                                        
         Done : Done                                                                
         Draft --> Ready                                                            
         Draft --> InProgress                                                       
         Draft --> Cancelled                                                        
         Ready --> InProgress                                                       
         Ready --> Blocked                                                          
         Ready --> Cancelled                                                        
         InProgress --> InReview                                                    
         InProgress --> Blocked                                                     
         InProgress --> Done                                                        
         InProgress --> Cancelled                                                   
         Cancelled --> Draft                                                        
         Blocked --> Ready                                                          
         Blocked --> InProgress                                                     
         Blocked --> Cancelled                                                      
         InReview --> InProgress                                                    
         InReview --> Done                                                          
         InReview --> Blocked                                                       
         InReview --> Cancelled                                                     
         Done --> InProgress                                                        
         Cancelled --> [*]                                                          
         Done --> [*]                                                               
                                                                                    
    
    feature lifecycle:                                                              
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Draft                                                              
         Draft : Draft                                                              
         Ready : Ready                                                              
         InProgress : InProgress                                                    
         Cancelled : Cancelled                                                      
         Blocked : Blocked                                                          
         InReview : InReview                                                        
         Done : Done                                                                
         Draft --> Ready                                                            
         Draft --> InProgress                                                       
         Draft --> Cancelled                                                        
         Ready --> InProgress                                                       
         Ready --> Blocked                                                          
         Ready --> Cancelled                                                        
         InProgress --> InReview                                                    
         InProgress --> Blocked                                                     
         InProgress --> Done                                                        
         InProgress --> Cancelled                                                   
         Cancelled --> Draft                                                        
         Blocked --> Ready                                                          
         Blocked --> InProgress                                                     
         Blocked --> Cancelled                                                      
         InReview --> InProgress                                                    
         InReview --> Done                                                          
         InReview --> Blocked                                                       
         InReview --> Cancelled                                                     
         Done --> InProgress                                                        
         Cancelled --> [*]                                                          
         Done --> [*]                                                               
                                                                                    
    
    task lifecycle:                                                                 
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Draft                                                              
         Draft : Draft                                                              
         Ready : Ready                                                              
         InProgress : InProgress                                                    
         Cancelled : Cancelled                                                      
         Blocked : Blocked                                                          
         InReview : InReview                                                        
         Done : Done                                                                
         Draft --> Ready                                                            
         Draft --> InProgress                                                       
         Draft --> Cancelled                                                        
         Ready --> InProgress                                                       
         Ready --> Blocked                                                          
         Ready --> Cancelled                                                        
         InProgress --> InReview                                                    
         InProgress --> Blocked                                                     
         InProgress --> Done                                                        
         InProgress --> Cancelled                                                   
         Cancelled --> Draft                                                        
         Blocked --> Ready                                                          
         Blocked --> InProgress                                                     
         Blocked --> Cancelled                                                      
         InReview --> InProgress                                                    
         InReview --> Done                                                          
         InReview --> Blocked                                                       
         InReview --> Cancelled                                                     
         Done --> InProgress                                                        
         Cancelled --> [*]                                                          
         Done --> [*]                                                               
                                                                                    
    
    bug lifecycle:                                                                  
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Open                                                               
         Open : Open                                                                
         InProgress : InProgress                                                    
         WontFix : WontFix                                                          
         Cancelled : Cancelled                                                      
         Fixed : Fixed                                                              
         Blocked : Blocked                                                          
         Verified : Verified                                                        
         Open --> InProgress                                                        
         Open --> WontFix                                                           
         Open --> Cancelled                                                         
         InProgress --> Fixed                                                       
         InProgress --> Blocked                                                     
         InProgress --> WontFix                                                     
         InProgress --> Cancelled                                                   
         WontFix --> Open                                                           
         Cancelled --> Open                                                         
         Fixed --> Verified                                                         
         Fixed --> InProgress                                                       
         Blocked --> InProgress                                                     
         Blocked --> WontFix                                                        
         Blocked --> Cancelled                                                      
         Verified --> InProgress                                                    
         WontFix --> [*]                                                            
         Cancelled --> [*]                                                          
         Verified --> [*]                                                           
                                                                                    
    
    decision lifecycle:                                                             
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Proposed                                                           
         Proposed : Proposed                                                        
         Accepted : Accepted                                                        
         Rejected : Rejected                                                        
         Superseded : Superseded                                                    
         Deprecated : Deprecated                                                    
         Proposed --> Accepted                                                      
         Proposed --> Rejected                                                      
         Accepted --> Superseded                                                    
         Accepted --> Deprecated                                                    
         Rejected --> Proposed                                                      
         Accepted --> [*]                                                           
         Rejected --> [*]                                                           
         Superseded --> [*]                                                         
         Deprecated --> [*]                                                         
                                                                                    
    
    review lifecycle:                                                               
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Requested                                                          
         Requested : Requested                                                      
         InReview : InReview                                                        
         Rejected : Rejected                                                        
         ChangesRequested : ChangesRequested                                        
         Approved : Approved                                                        
         Requested --> InReview                                                     
         Requested --> Rejected                                                     
         InReview --> ChangesRequested                                              
         InReview --> Approved                                                      
         InReview --> Rejected                                                      
         ChangesRequested --> InReview                                              
         ChangesRequested --> Approved                                              
         ChangesRequested --> Rejected                                              
         Rejected --> [*]                                                           
         Approved --> [*]                                                           
                                                                                    
    
    guide lifecycle:                                                                
    
                                                                                    
     stateDiagram-v2                                                                
         [*] --> Draft                                                              
         Draft : Draft                                                              
         Published : Published                                                      
         Deprecated : Deprecated                                                    
         Draft --> Published                                                        
         Published --> Deprecated                                                   
         Published --> Draft                                                        
         Deprecated --> Published                                                   
         Published --> [*]                                                          
         Deprecated --> [*]                                                         
                                                                                    
    
    Retype                                                                          
    
    Reclassify a work item to a different type — the sequence number (and durable   
    identity) is preserved; only the ID prefix changes. All incoming refs,          
    children's parent links, and prose mentions are rewritten to the new ID         
    atomically.                                                                     
    
                                                                                    
     sq <type> <n> retype <new-type>   # e.g. sq task 7 retype bug                  
                                                                                    
    
    Valid targets: epic, feature, task, bug, decision, review, guide.               
    
    Status behaviour: when the old and new types share the same workflow (e.g.      
    epic↔feature↔task) the status is carried as-is; otherwise the status resets to  
    the new type's initial value and the command says so.                           
    
    Refusals with actionable hints:                                                 
    
     • item has sub-entities (clear them first)                                     
     • existing parent would be invalid for the new type (re-parent or remove the   
       parent first)                                                                
     • any child would become invalid under the new type (re-parent or remove those 
       children first)                                                              
    
    After retype, sq check is clean and sq repair is a stable no-op.                
    
    Remove vs. Cancel                                                               
    
    Two distinct exit paths for work items — use the right one:                     
    
                                                                                    
              Cancel                             Remove                             
     ────────────────────────────────────────────────────────────────────────────── 
     Intent   Work genuinely considered, then    Item should never have existed     
              dropped                            (mis-creation, test artifact,      
                                                 rolled-back decision)              
     Effect   Status → Cancelled; item stays on  File deleted, index entry gone;    
              the books, greppable, linkable,    only a sequence-number gap remains 
              visible in tree/list                                                  
     Command  sq <type> <n> status Cancelled     sq <type> <n> remove               
                                                                                    
    
                                                                                    
     sq <type> <n> status Cancelled   # drop work that was genuinely considered     
     sq <type> <n> remove             # erase a mis-creation (interactive confirm)  
     sq <type> <n> remove --yes       # skip the confirm                            
     sq <type> <n> remove --force     # also sever incoming refs from referrers'    
     frontmatter                                                                    
                                                                                    
    
    Ref and child safety:                                                           
    
     • remove refuses when the item has incoming refs or children, listing every    
       offender.                                                                    
     • --force severs refs but still refuses while children exist; re-parent or     
       remove children first.                                                       
     • After any removal sq check is clean — no dangling refs, no dangling parent   
       links.                                                                       
    
    Sequence gaps are sanctioned, not corruption. Removal deletes the index entry   
    but never touches the counter high-water mark — the freed number is never       
    reissued.  A gap means "an item with that sequence number existed and was       
    removed."  sq check and sq repair treat gaps as normal; the reflog records a    
    reconstructable removal line that explains each gap.                            
    
    Ref kinds                                                                       
    
    The vocabulary is closed — exactly eight kinds, no custom extensions in 1.0. Use
    sq <type> <n> ref add <id> --kind <kind>.                                       
    
                                                                                    
     Kind        Meaning               Direction convention   Consumer              
     ────────────────────────────────────────────────────────────────────────────── 
     related     Generic               A related B lives on   Navigation            
                 cross-reference       A                                            
                 (default)                                                          
     blocks      A is blocking B; B    A blocks B lives on A  sq blocked            
                 cannot proceed while  (the blocker)                                
                 A is open                                                          
     depends-on  A depends on B; A     A depends-on B lives   sq blocked            
                 cannot proceed while  on A (the dependent)                         
                 B is open.                                                         
                 Equivalent to B                                                    
                 blocks A — A                                                       
                 depends-on B ≡ B                                                   
                 blocks A                                                           
     implements  A implements the      A implements B lives   Navigation            
                 requirement or spec   on A                                         
                 described by B                                                     
     fixes       A (a task or PR)      A fixes B lives on A   sq check task rules   
                 fixes bug B                                                        
     addresses   A (a task) addresses  A addresses B lives    sq check task rules   
                 or follows up review  on A                                         
                 B                                                                  
     supersedes  A (a newer decision)  A supersedes B lives   sq check decision     
                 supersedes B (an      on A (the newer        warnings              
                 older one); B's       decision)                                    
                 status should be                                                   
                 Superseded                                                         
     duplicates  A (a later filing)    A duplicates B lives   Navigation            
                 duplicates B (the     on A (the later                              
                 original); A is       filing)                                      
                 usually closed as                                                  
                 Cancelled                                                          
                                                                                    
    
    blocks and depends-on are two spellings of the same dependency: use whichever   
    fits your authoring context. Bare ref add <id> (no --kind) defaults to related.  callback and ; prints workflow.md.j2 verbatim (markdown tables + fenced mermaid) instead of piping through rich.Markdown, mirroring sq show --raw / sq docs.
  - New golden tests/goldens/workflow_cheatsheet_raw.txt + tests/cli/test_workflow_raw_markdown_golden.py (byte-identical to the pre-existing render()-level workflow_cheatsheet.txt golden plus the CLI trailing newline).
  - Scoped tests + tests/meta + pyright + ruff all green; sq check clean. @reviewer over to you.
- [2026-07-17T14:05:13Z] Elias Python:
  - Correction — previous comment got mangled by shell backtick expansion. Restating:
  - Added --raw to both the bare "sq workflow" callback and "show"; prints workflow.md.j2 verbatim (markdown tables + fenced mermaid) instead of piping through rich.Markdown, mirroring the "sq show --raw" / "sq docs" precedent.
  - New golden tests/goldens/workflow_cheatsheet_raw.txt + tests/cli/test_workflow_raw_markdown_golden.py (byte-identical to the pre-existing render()-level workflow_cheatsheet.txt golden, plus the CLI trailing newline). CHANGELOG updated.
  - Scoped tests + tests/meta + pyright + ruff all green; sq check clean. @reviewer over to you.
<!-- sq:discussion:end -->
