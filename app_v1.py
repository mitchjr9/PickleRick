"""
Pickle Rick — Your Pickleball Rules Assistant
==============================================
Single-file Streamlit app — pickleball rules AI assistant trained on the
2026 USA Pickleball Official Rulebook + 2026 Rulebook Change Document.

Tabs: 🥒 Home/Chat | 🎬 Video Analyzer | 📝 Quiz
Run:  streamlit run app.py
"""

# ── Standard library ──────────────────────────────────────────────────────────
import base64
import datetime
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

# ── Third-party ───────────────────────────────────────────────────────────────
import anthropic
import streamlit as st

# ── OpenCV — auto-install if missing ─────────────────────────────────────────
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "opencv-python-headless", "-q"]
        )
        import cv2
        OPENCV_AVAILABLE = True
    except Exception:
        OPENCV_AVAILABLE = False


# =============================================================================
# CORE KNOWLEDGE BASE — 2026 USA Pickleball Official Rulebook + Change Document
# =============================================================================
# This is the permanent brain of Pickle Rick. Every rule citation here comes
# directly from the two project PDFs. Update this string when new rule changes
# or personal notes are added.

CORE_KNOWLEDGE = """
# Pickle Rick Core Knowledge Base
## 2026 USA Pickleball Official Rulebook + 2026 Change Document

> **CRITICAL INSTRUCTION FOR ALL RESPONSES:**
> The 2026 USA Pickleball Official Rulebook (effective January 1, 2026) is the
> authoritative source. The 2026 Rulebook Change Document explains every rule
> that changed from 2025 → 2026. Always cite the specific 2026 rule number
> (e.g., "Rule 7.C.1") and reference the 2025→2026 change when relevant.
> If a player asks about something using 2025 rule numbers (e.g., "Rule 4.A.7"),
> map it to the new 2026 rule number using Section 0 below.

---

## 0. 2025 → 2026 RULE CHANGE QUICK MAP

| # | 2025 Rule | 2026 Rule | Topic |
|---|-----------|-----------|-------|
| 1 | 4.M.4 | **7.E.1** | Serve must land in correct service court (clarification) |
| 2 | 11.K | **10.C.5** | Net post — ball that bounces in then hits net post = winner for hitter |
| 3 | 12.C.4.a | **15.B.4.a** | Round robin withdrawals/retirements/forfeits |
| 4 | 9.B.1 | Definition | "Act of Volleying" definition added |
| 5 | 12.C.4 | **15.B.4** | Round robin tiebreaker process |
| 6 | 13.C.2.a | **8.J** | Spectators must NOT be consulted on calls |
| 7 | 3.A.5 | Deleted | "Cross-court" definition removed |
| 8 | 13.M.2 | **22.L, 22.L.2** | Ejections for assault |
| 9 | 13.M | **22.L, 22.L.5** | Ejections for willful damage to property |
| 10 | 13.G.3.e | **22.A** | Penalties before match starts |
| 11 | 11.A | **10.D, 10.D.1, 10.D.2** | Double-hit rule clarified |
| 12 | 13.C.4.b | **17.C.2** | Pre-match briefing |
| 13 | 6.C.8 | **8.H** | "Doubt" → "Conflict" on partner disagreement |
| 14 | 12.B.1.c | **4.B** | Game potentially won by a technical foul |
| 15 | 4.A.5 | **7.B.2** | Paddle adding spin to ball at contact during serve — **NOW LEGAL by paddle** |
| 16 | 6.C.7 | **8.F, 8.F.3** | Prompt line calls |
| 17 | 10.B.2.C | **21.C.9** | Doubles player retirement, partner continues |
| 18 | 13.J | **20.J, 20.J.1** | Rescinding a Head Referee call |
| 19 | 10.B | **21.C.4** | Rescinding medical time-out |
| 20 | 12.B.1.c | **4.B, 14.A.2** | Rally scoring — winning point: **receiver CAN now win on game point** |
| 21 | — | **25.A** | NEW: Wheelchair player rules (extensive new section) |
| 22 | — | **25.A.4** | NEW: Wheelchair is an extension of the body |
| 23 | 4.A.7 | **7.C** | "Flat serve" — "clearly" added — stronger enforcement |
| 24 | 4.K | **6.F** | Wrong score called — process clarified |
| 25 | — | **25.B** | NEW: Adaptive standing player rules |
| 26 | 7.N | **24.B** | Extra ball visible/dropped = fault (stricter) |
| 27 | — | **8.J** | Spectators may NOT be consulted on calls |
| 28 | — | **19.G** | Officiated line-call procedure clarified |
| 29 | 10.A.3 | **21.A.2** | Time-out must be called audibly/visibly |

> **HEADLINE 2026 CHANGES TO REMEMBER:**
> 1. **Rally scoring receiver CAN win on game-point** (Rule 4.B, 14.A.2) — change #20
> 2. **Spin allowed on paddle contact during serve** — but NEVER on hand release (Rule 7.B.2) — change #15
> 3. **Net post: ball that bounces in then hits net post = WINNER for hitter** (Rule 10.C.5) — change #2
> 4. **Partner "doubt" is now "conflict"** — disagreement = ball is "in" (Rule 8.H) — change #13
> 5. **Volley serve: "clearly" added** to upward arc, paddle-head, ball-height (Rule 7.C) — change #23
> 6. **Time-outs MUST be audibly/visibly signaled** (Rule 21.A.2) — change #29
> 7. **Extra ball visible or dropped = fault** (Rule 24.B.1) — change #26
> 8. **Spectators must NOT be consulted on calls** (Rule 8.J) — change #6
> 9. **NEW Wheelchair (25.A), Adaptive Standing (25.B), Hybrid Doubles (25.C) sections**
> 10. **Ejection/expulsion** for paddle/ball assault or willful property damage (Rule 22.L) — changes #8, #9

---

## 1. THE GAME — Section 1 (p. 1)

Pickleball is played on a 20 ft × 44 ft court with a perforated ball and tennis-style net.
- **Standard scoring:** Points scored only by serving team. First to 11, win by 2.
- **Rally scoring (provisional, Rule 14.A / 15.C.2):** Point on every rally.
  - **2026 change:** Receiver CAN now win on game point — point awarded on every rally regardless of who serves (Rule 4.B, 14.A.2; Change #20).
- **Two-Bounce Rule:** Receiver must let serve bounce. Then serving team must let return bounce. (Rule 10.A)
- **Non-Volley Zone (NVZ):** 7 ft × 20 ft area on each side of net where you cannot volley. (Rule 3.A.4.c)

---

## 2. KEY DEFINITIONS — Section 2 (pp. 2–4)

- **Fault:** A rules violation resulting in dead ball + loss of rally.
- **Hinder:** Transient element NOT caused by a player (stray balls, insects, foreign material). Permanent objects are NOT hinders.
- **Distraction (player-caused):** Physical actions not common to the game that interfere with opponent's ability to hit the ball. Examples: loud noises, stomping, erratic paddle waving. (10.F, 20.I)
- **Volley:** A strike of the ball before the ball bounces.
- **Volleying, Act of:** Begins when the ball is hit out of the air (i.e., volleyed) and ends when the player's follow-through momentum stops. (NEW definition — Change #4)
- **Momentum:** Property of a body in motion that causes a player to continue moving after contacting the ball. Ends when player regains balance/control or stops moving toward NVZ.
- **Permanent Object:** Anything on/above/near court that can interfere — ceilings, walls, fencing, lighting, **net posts (including connected wheels, arms, legs)**, net cable/rope on top of net post, stands, seats, spectators in recognized positions, referee, line judges.
- **Imaginary Extension:** Continuation of a line beyond its physical endpoint (used for serving area boundaries, etc.).
- **Live Ball:** From start of score call until ball becomes dead.
- **Technical Warning:** Punitive warning for minor unsportsmanlike behavior.
- **Technical Foul:** One-point penalty for extreme unsportsmanlike behavior.
- **Verbal Warning:** Non-punitive caution (NEW classification).

---

## 3. COURT & EQUIPMENT — Section 3 (pp. 5–10)

**Court (Rule 3.A):** 20 ft × 44 ft (6.10 m × 13.41 m).
- **NVZ (Rule 3.A.4.c):** 7 ft × 20 ft. **All NVZ lines ARE PART OF THE NVZ.** The NVZ is **2-dimensional and does NOT extend above the playing surface.** This is critical — you can lean over the NVZ without faulting if you don't touch it.
- **Service courts (3.A.4.f):** Each service court is bounded by and **includes** its baseline, sideline, and centerline.
- **Serving area (3.A.4.g):** Behind baseline, bounded by **imaginary extensions** of sideline and centerline.
- **Lines (3.A.4.e):** 2 inches wide, contrasting color.

**Net (Rule 3.B):** 36" at sidelines, 34" at center.

**Ball (Rule 3.C):** Approved ball list. Indoor balls have larger holes; outdoor balls have smaller holes.

**Paddle (Rule 3.D):**
- 3.D.2 — Combined length+width ≤ 24"; length ≤ 17". No thickness restriction.
- 3.D.3 — No weight restriction.
- 3.D.1 — Must have brand/model marking + "USA Pickleball Approved" seal/text.
- Must be on USA Pickleball Approved Paddle List for sanctioned play.
- 18.A.2 — **Match forfeit** if non-compliant paddle discovered DURING play. No penalty to switch BEFORE match (18.A.1).

---

## 4. SCORING & WINNING THE GAME — Section 4 (pp. 10–11)

- **4.A — Standard scoring:** Point only when serving team wins rally.
- **4.B — Winning the Game (2026 NEW WORDING):** "The first singles player or doubles team to score the winning point wins the game." — Change #14, #20.
  - **Implication:** In rally scoring, a receiving team CAN win the game by winning a rally on game point. Also: if the serving team is at 0 and assessed a technical foul when receiver is at game point, the receiver gets the point AND the game.

---

## 5. PLAYER POSITIONS & SERVING SEQUENCE — Section 5 (pp. 12–13)

**Singles (5.A):**
- Score 0 or even → serve from RIGHT, into opponent's right court.
- Score odd → serve from LEFT, into opponent's left court.

**Doubles (5.B):**
- Both players serve before side-out, **except** at start of game (only starting server serves before first side-out).
- 5.B.2 — After side-out, the player on the correct side per team's score becomes the **first server**; partner is **second server**. The first-game starting server is designated as a "second server" for the team's first service rotation.
- 5.B.3 — Starting server on RIGHT when team score is 0/even; LEFT when odd. Partner is opposite.
- 5.B.4 — Except while serving/receiving, **no restriction on player positions during rallies**.

**5.C — Player/Position Errors:**
- 5.C.1.a — Replay if correct claim during rally.
- 5.C.1.b — **Fault if INCORRECT claim** that stopped the rally.
- 5.C.1.c — **Fault on incorrect receiver** even if rally was completed (must be called before next serve).
- 5.C.2 — If positions wrong but rally completed and no one stopped it, result stands.

---

## 6. PLAYER READINESS & SCORE CALLING — Section 6 (pp. 14–15)

- 6.D — Server has 10 seconds to serve after score call.
- 6.D.2 — If serving team changes serving areas after score is called, replay/repostion + re-call score (restarts 10-sec count).
- 6.E — "Stop" or "wait" before serve is hit will be recognized.
- **6.F — Challenging the Score Call (CHANGE #24):**
  - 6.F.1 — Replay if incorrect score caught BEFORE return of serve and ball still live.
  - 6.F.2 — **Fault** if a player stops a rally to challenge a CORRECT score.
  - 6.F.3 — **Fault** if challenge made AFTER return of serve.
  - 6.F.4 — If incorrect score discovered after rally completes, rally result stands; correct score before next serve.

---

## 7. SERVING — Section 7 (pp. 16–18) ★ HIGHLY TESTED ★

**7.A — Server Positioning (when serve is hit):**
- 7.A.1 — At least one foot must contact the correct serving area. (Fault 7.A.1.a — Server Not Grounded)
- 7.A.2 — Neither foot may contact the court. (Fault 7.A.2.a — Server Contacting Court)
- 7.A.3 — Neither foot may contact playing surface OUTSIDE the correct serving area. (Fault 7.A.3.a — Server Outside Serving Area) — bounded by imaginary extensions.

**7.B — Ball Release:**
- 7.B.1 — Release ball using ONLY one hand OR only the paddle.
- 7.B.2 — **No manipulation/spin upon release** by any body part or paddle. Exception: ball may roll off paddle face by gravity.
  - **2026 CHANGE #15:** "Spin may be applied to the ball upon contact by the paddle." Spin via PADDLE at contact = LEGAL. Spin via HAND on release = ILLEGAL.
- 7.B.2.a — Replay if receiver determines manipulation/spin (must call before returning serve).
- 7.B.3 — Server's release must be VISIBLE to receiver.
- 7.B.3.a — Receiver may call replay before return if release was not visible.

**7.C — Volley Serve (CHANGE #23 — "clearly" added for stronger enforcement):**
- 7.C.1 — Paddle must be moving in a **clear** upward arc at contact.
- 7.C.2 — Highest point of paddle head must **clearly** NOT be above highest part of server's wrist joint at contact.
- 7.C.3 — Ball must **clearly** be no higher than server's waist at contact.
- 7.C.4 — Forehand or backhand allowed.
- 7.C.5 — Fault if 7.C.1, 7.C.2, or 7.C.3 violated.

**7.D — Drop Serve:**
- 7.D.1 — Release from natural (unaided) height.
- 7.D.2 — Ball must NOT be propelled in any direction or any manner before being struck.
- 7.D.3 — No restriction on # of bounces before strike.
- 7.D.4 — No restriction on bounce location.
- 7.D.5 — Forehand or backhand.
- 7.D.6 — Fault if 7.D.1 or 7.D.2 violated.
- **NOTE:** Drop serve has NO upward-arc / paddle-head / waist-height requirements.

**7.E — Serve Placement:**
- Must serve diagonally to opposite service court. Must clear NVZ. May or may not touch net.
- 7.E.1 — Fault: serve lands outside correct service court (CHANGE #1).
- 7.E.2 — Fault: serve lands in NVZ (NVZ line counts as IN the NVZ → fault).
- 7.E.3 — Fault: serve hits permanent object before landing.
- 7.E.4 — Fault: serve hits server or server's partner (or anything worn/carried).
- 7.E.5 — Fault: serve hits receiver or receiver's partner before landing → fault on RECEIVER (point to server).

---

## 8. LINE CALLS — Section 8 (pp. 19–20) ★ CRUCIAL FOR REC PLAY ★

- 8.A — Players responsible for "out" calls on THEIR end of the court. Either doubles partner may call.
- 8.B — "In" ball: served ball that clears NVZ line and lands in correct service court is "in." Returned ball that lands on opponent's end is "in."
- 8.C — "Out" ball: served ball not landing in correct service court (including landing ON the NVZ line) is "out." Any other ball outside court is "out."
- **8.D — Code of Ethics:** "All questionable calls must be resolved in favor of the opponent. The opponent gets the benefit of the doubt. **Any ball that cannot be promptly called 'out' must be considered 'in.'**"
- **8.E — Line Call Certainty:** "Players must NOT call a ball 'out' unless they can clearly see a SPACE between the line and the ball when it lands." (Figure 8-1)
- 8.F — "Out" must be promptly signaled audibly OR visibly OR both.
  - 8.F.1 — Any "out" call after the ball lands is a line call.
  - 8.F.2 — Line call → dead ball.
  - 8.F.3 — **Out-call timing (CHANGE #16):** If you RETURN the ball, the "out" call must be made before opponent hits ball or before ball becomes dead, otherwise play continues. If you DON'T return the ball, a prompt "out" call counts even if ball is already dead.
  - 8.F.4 — Partner communication while ball is in air ("out!" "no!" "bounce it!") = communication, NOT a line call.
- 8.G — Players may override own/partner's call to disadvantage themselves.
- **8.H — Partner Disagreement (CHANGE #13):** "When partners disagree on a line call, then conflict exists, and the team's call will be 'in.'" (was "doubt" pre-2026)
- 8.I — Asking opponent's opinion: opponent's clear in/out decision stands. If no definitive call, your call stands; if you made no call, ball is "in." After asking, you & partner LOSE the chance to call (except to override in opponent's favor).
- **8.J — Spectator Involvement (CHANGE #6):** "Spectators must not be consulted on any call."

---

## 9. DEAD BALLS, FAULTS & HINDERS — Section 9 (pp. 21–22)

- 9.A.1 — **Fault** if you stop a rally before ball becomes dead, UNLESS you're calling a hinder, correctly identifying position/server error, or correcting a wrong score before return.
- 9.B.1 — Faults only occur while ball is live, EXCEPT NVZ momentum violations (11.A.2) that occur after dead ball.
- 9.B.3 — **Players may ONLY call NVZ faults & service foot faults on opponents.**
  - 9.B.3.b — Disagreement between teams on a fault → REPLAY.
  - 9.B.3.c — Disagreement between partners → benefit of opponents.
- 9.B.4 — For other faults (besides NVZ + service foot fault), you may mention to opponent but cannot enforce — final call is on the alleged offender.
- 9.C.1 — Any player may call a hinder.
- 9.C.2 — Called hinder = REPLAY.

---

## 10. RALLY SITUATIONS — Section 10 (pp. 23–24)

- **10.A — Two-Bounce Rule:**
  - 10.A.1 — Fault: receiver volleys serve.
  - 10.A.2 — Fault: serving side volleys return of serve.
- 10.B.1 — Fault: ball not returned before second bounce.
- **10.C — Returned Ball Placement Faults:**
  - 10.C.1 — Lands out of bounds.
  - 10.C.2 — Lands on hitter's side (failed to cross net).
  - 10.C.3 — Hits player or anything worn/carried EXCEPT paddle/hand below wrist while holding paddle.
  - 10.C.4 — Hits permanent object before landing.
  - **10.C.5 — Hits permanent object AFTER landing on hitter's court (CHANGE #2).** Net post is a permanent object. **If a ball crosses net, bounces in opponent's court, and THEN (due to spin/wind) touches the net post → POINT for the hitter.** This is the "net post winner" rule.
- **10.D — Double Hit (CHANGE #11):**
  - 10.D.1 — Fault if ball is hit more than once unless the stroke is **continuous and in a single direction** by ONE player.
  - 10.D.2 — Fault if both partners strike the ball.
- 10.E — Missed shot (whiff) → ball remains live.
- 10.F — Distraction (player-caused) prohibited; see 20.I.1.
- 10.G — Damaged ball: play continues to end of rally. Replace if all agree (10.G.1 — replay if all agree it affected outcome; 10.G.2 — soft/degraded ball: prior rally stands).
- 10.H — Injury during rally: play continues to end of rally.
- 10.I — Equipment problem during rally: play continues.
- 10.J — Item dropped on YOUR side: ball remains in play (even if it hits the item) — UNLESS item contacts NVZ as a result of you volleying (then NVZ fault per 11.A.1).
- 10.K — Between rallies: quick hydration/towel/equipment OK if game flow not impacted.

---

## 11. NON-VOLLEY ZONE INFRACTIONS — Section 11 (p. 25) ★★★

**Allowable Contact (11.A):** All volleys must be **initiated outside** the NVZ. A player or anything in contact with the player may contact the NVZ AT ANY TIME except during the act of volleying.

**Faults:**
- **11.A.1 — NVZ Contact While Volleying.** When a volleying player (or anything in contact with that player, including their partner) touches the NVZ. Includes hat/sunglasses/paddle that fall in NVZ during a volley.
- **11.A.2 — NVZ Momentum.** When a volleying player's momentum causes them to contact anything (including their partner) that is in contact with the NVZ — **even AFTER the ball becomes dead.** (This is the famous "you can't fall in the kitchen" rule.)
- **11.A.3 — Failure to Exit NVZ Before Volleying.** After contacting the NVZ, you must establish BOTH FEET completely outside the NVZ before volleying.

**Critical points referees miss most often:**
1. NVZ is 2D — leaning over without contact is FINE.
2. You can stand in NVZ all day if you're not volleying.
3. Momentum fault counts even if you've already won the rally.
4. Dropping your paddle in NVZ during a volley = fault.
5. Partner pushing you into NVZ during your volley = your fault (or theirs if anything they wear/carry contacts NVZ during your volley).

---

## 12. THE PADDLE DURING PLAY — Section 12 (p. 26)

- 12.A.1 — Fault: more than one paddle during a rally.
- 12.B — Must have possession when hitting; one or both hands; can switch hands anytime.
- 12.B.1 — Fault: not in possession at contact.
- 12.C.1 — Fault: catch or carry ball on paddle ("scoop").

---

## 13. NET & NET SUPPORT SYSTEM — Section 13 (pp. 27–29)

- 13.A — Ball contacting net itself: ball remains in play. (13.A.1 — replay if ball gets caught in net or contacts a draping/deflecting net.)
- 13.B.1 — Fault: served ball contacts net support system on either end; or returned ball contacts net support system on hitter's end before crossing net.
- 13.B.2 — Replay: returned ball crosses net then contacts crossbar/support system within court boundaries.
- 13.C — Ball may be returned around outside of net post (Aussie shot — legal!).
- 13.D.1 — Fault: ball hit between net and net post.
- 13.E.1 — Fault: ball hit under net.
- **13.F.1 — Fault: ball hit before it entirely crosses plane of net to your end** (no reaching over).
- 13.G.1 — Fault: player or anything worn/carried contacts net or net support system while ball is live.
- 13.H.1 — Fault: contacting opponent or opponent's court while ball is live.
- **13.I — Plane of Net (Reaching Over):**
  - 13.I.1 — May cross plane IMMEDIATELY AFTER hitting (follow-through OK while executing strike).
  - 13.I.1.a — Fault: cross plane BEFORE hitting.
  - 13.I.1.b — Fault: cross plane and DON'T hit.
  - 13.I.2 — Spin-back ball (e.g., severe backspin causes ball to cross net back to opponent's side without being touched): receiver may go around/over/under net to play it — but only AFTER the ball has crossed back.
    - 13.I.2.a — Fault: crossing plane BEFORE ball crosses back.
    - 13.I.2.b — Fault: failing to hit it before second bounce on opponent's end.
- 13.J — Replay if net system malfunctions during rally.

---

## 14. RALLY SCORING (Provisional) — Section 14 (pp. 30–34)

- 14.A.2 — **Point scored by player/team that wins each rally** (CHANGE #20).
- 14.B — Mini-singles: half-court singles variation. Server's side determines diagonal court; receiver's score determines their side.
- See also 15.C.2 for tournament rally scoring formats.

---

## 15. TOURNAMENT MATCH/SCORING OPTIONS — Section 15 (pp. 35)

- 15.C.1 — Standard scoring formats: 2-of-3 to 11; 3-of-5 to 11; one game to 15 or 21; round robin one-game to 11 (6+ teams).
- 15.C.2 — **Provisional rally scoring formats** — TD's option, NOT permitted in double-elim doubles, 2026 USAP Golden Ticket events, or 2026 USAP National Championship events.
- 15.F — Two-match minimum per event entered (except single-elim w/o consolation).

---

## 16. TOURNAMENT DIRECTOR — Section 16 (pp. 37–38)

- 16.F — TD **must NOT** implement any rule not in the Rulebook. Exceptions for physical court limitations require pre-approval by USA Pickleball Managing Director of Officiating.
- 16.G — TD chooses the tournament ball from approved list.
- 16.K — TD may require apparel changes.

---

## 17. REFEREE DUTIES — Section 17 (pp. 39–40)

- 17.D.2 — Call score after confirming correct server.
- 17.D.4 — Call "second server" after first server's team loses rally.
- 17.D.5 — Announce "side out" when singles player or second server loses serve.
- 17.D.8 — Call faults when they occur.
- 17.D.10 — Assist with line calls upon appeal or when line judge signals blocked view.
- 17.D.13 — Call hinders / determine validity of player-called hinders.
- 17.D.16 — 15-second warnings during time-outs.

---

## 18. PLAYER PRE-MATCH — Section 18 (p. 42)

- 18.A.1 — Non-compliant paddle BEFORE match → switch, no penalty.
- 18.A.2 — Non-compliant paddle DURING match → **match forfeit**.
- 18.A.3 — Discovered AFTER match → results stand.
- 18.B.3 — Apparel approximating ball color must be changed (referee time-out used).
- 18.C — Starting servers must wear ID determined by TD (visible during play).

---

## 19. TOURNAMENT LINE CALLS — Section 19 (pp. 44–46)

- 19.A.1 — Referee responsible for service foot faults, short serves, NVZ faults.
- 19.B — No line judges → players make all "out" calls on their end.
- **19.C — With line judges:**
  - 19.C.1 — Line judges call their assigned line + assist as requested ("OUT" + outstretched arm).
  - 19.C.2 — Players responsible only for centerline of service court on their end.
  - 19.C.3 — Player line calls invalid except centerline + override to favor opponent.
- 19.D — Only RALLY-ENDING shots can be appealed. Appeal before next serve hit (or before scoresheet initialed for match-ending shot).
- 19.F — Referee may overrule line judge's "out" call (19.F.2 → replay).
- 19.G — All officials uncertain → referee may consult; if all unable → replay.

---

## 20. TOURNAMENT MATCH SITUATIONS — Section 20 (pp. 47–51)

- 20.A — Any player may ask referee for correct score before serve hit.
- 20.B — Any player may ask referee to confirm correct server/receiver/positions before serve hit.
- 20.D — After score is called, if serving team changes serving areas → referee stops play, allows reposition, re-calls score.
- **20.E — Service Faults (referee-called):**
  - 20.E.1.a — Volley serve: no upward arc.
  - 20.E.1.b — Volley serve: paddle head clearly above wrist.
  - 20.E.1.c — Volley serve: ball clearly above waist.
  - 20.E.1.d — Volley/drop serve: not clearly released from one hand or paddle only.
  - 20.E.1.e — Volley/drop serve: spin or manipulation on release.
  - 20.E.1.f & 20.E.1.g — additional service faults.
  - 20.E.2 — Replays when referee uncertain whether serve requirements met.
- **20.H — Hinder (CHANGE: referee must validate):**
  - 20.H.1 — Fault if invalid (referee doesn't validate).
  - 20.H.2 — Replay if valid.
- **20.I — Distraction:**
  - 20.I.1 — Fault if referee judges player distracted opponent about to hit ball.
- **20.J — Officiating Decision Challenge (CHANGE #18):**
  - 20.J.1 — Rescinding challenge after referee acknowledged → standard time-out charged (or technical foul if none available).
  - 20.J.2 — Challenge UPHELD → technical warning + standard time-out (or tech foul if no TO).
  - 20.J.3 — Challenge OVERTURNED → reverse ruling or order replay.
- 20.K — Referee may remove a line judge for cause.

---

## 21. TIME-OUTS & BREAKS — Section 21 (pp. 52–55)

**21.A — Standard Time-Outs:**
- 21.A.4 — Two 1-minute time-outs per game in 11-point format; three in 15- or 21-point.
- **21.A.2 — Requesting Time-Out (CHANGE #29):** Must be called audibly by voice OR visibly by hand, OR both, directed toward opponents and referee.
  - 21.A.2.a — Fault: time-out called AFTER serve is hit.
  - 21.A.2.b — Verbal/technical warning if not called audibly/visibly (delay of game).

**21.B — End Changes:**
- 21.B.1 — In 11-point game: at score of 6.
- 21.B.2 — In 15-point game: at score of 8.
- 21.B.3 — In 21-point game: at score of 11.
- 21.B.4 — Same server continues after end change.
- 21.B.5 — Max 1 minute.
- 21.B.7 — If end change missed, execute when detected (no fault, score unchanged, same server).

**21.C — Medical Time-Out (CHANGE #19):**
- 21.C.1 — Cannot be called before match starts.
- 21.C.3 — One per match.
- 21.C.4 — **Rescinding after medical called and BEFORE arrival → standard TO charged; medical TO not charged.** No standard TO available → tech foul (delay of game).
- 21.C.6 — Max 15 minutes (off-court treatment travel time excluded).
- 21.C.7 — Timer starts when medical assistance arrives.
- 21.C.9 — Match retirement if can't continue after 15 min (CHANGE #17 — partner may continue in doubles per rules).
- 21.C.10 — Invalid medical condition → technical warning + standard TO charged (or tech foul if none).
- 21.C.11 — Resume with 15-second warning.

**21.D — Referee Time-Out:**
- 21.D.1 — Referee can call for safety / potential medical.
- 21.D.2 — **Bleeding/blood**: stop at end of rally, must control bleed and clean before resuming.
- 21.D.3 — Foreign substances must be cleaned.

**21.E — Equipment Time-Out:** Reasonable duration if needed for fair/safe continuation.

---

## 22. PLAYER CONDUCT, WARNINGS & PENALTIES — Section 22 (pp. 56–60)

**22.A — Verbal Warnings:** Non-punitive caution for minor unsportsmanlike behavior. No effect on rally/score/server.

**22.B — Technical Warnings (non-exhaustive):**
- 22.B.6 — Excessive line-call appeals.
- 22.B.7 — Coaching during rally (also see 20.G.1).
- 22.B.8 — **Lost ruling challenge (TO available)** → tech warning + standard TO. (See 20.J.2.)
- 22.B.9 — **Invalid medical TO request (TO available)** → tech warning + standard TO. (See 21.C.10.)
- 22.B.10 — Other minor unsportsmanlike behavior.

**22.C — Verbal/Technical Warning Consequences:**
- 22.C.1 — No loss of rally or point.
- 22.C.2 — No effect on server.

**22.D — Technical Fouls (extreme unsportsmanlike conduct):**
- 22.D.1 — **Paddle abuse** (negligent/reckless throw not striking person or property).
- 22.D.2 — **Ball abuse** (aggressively/recklessly throwing/hitting dead ball).
- 22.D.3 — Extreme objectionable language/profanity.
- 22.D.4 — Threats.
- 22.D.5 — Lost ruling challenge — no TO available.
- 22.D.6 — Invalid medical TO — no TO available.
- 22.D.7 — Second technical warning during a match.
- 22.D.8 — Other extreme unsportsmanlike behavior.

**22.E — Tech Foul Consequences:**
- **22.E.1 — Score adjustment: −1 from offender (or +1 to opponent if offender at 0).** Player/team must move to correct position based on new score. **Game-winning point can result if adjustment makes the score game-winning, regardless of who was serving.**
- 22.E.2 — No effect on server (no side-out from tech foul itself).

**22.F — Game Forfeit:**
- 22.F.1 — Combination of one tech warning + one tech foul (or three tech warnings) during match → game forfeit.
- 22.F.2 — Late reporting for first game (Rule 18.F.1).

**22.I — Match Forfeit by Referee:**
- 22.I.1 — Dangerous paddle/ball abuse striking person or damaging property.
- 22.I.5 — Non-compliant paddle (Rule 18.A.2).
- 22.I.6 — Improper deliberately aggressive physical contact.
- 22.I.7 — Second tech foul, OR tech warning/foul after a game forfeit from prior tech accumulation.

**22.J — Match Forfeit by TD:** Venue rules, improper between-match conduct, facility abuse, improper apparel, other rules.

**22.K — Forfeit Scoring:** All forfeit games reported as 11-0, 15-0, or 21-0.

**22.L — Ejection or Expulsion (CHANGES #8, #9):**
- 22.L.2 — **Injurious paddle/ball abuse** or other physical violence — ejection from tournament.
- 22.L.5 — **Willful damage** to venue property — ejection.

---

## 23. NON-OFFICIATED & UNOFFICIATED PLAY

- 24.A — Non-officiated tournament play uses Sections 1–14 + Section 24.
- **24.B — Extra Ball (CHANGE #26):**
  - Must not be visible to opponent + must remain in player's possession.
  - 24.B.1 — Fault if extra ball visible to opponent OR falls to playing surface while ball is live.

---

## 24. WHEELCHAIR / ADAPTIVE STANDING / HYBRID — Section 25 (pp. 65–71) ★ NEW IN 2026 ★

**25.A — Wheelchair Play (Changes #21, #22):**
- 25.A.4 — **Wheelchair is part of player's body. Large rear wheels = legs for positioning.**
- 25.A.5 — Player must contact seat (with allowed exceptions per 25.A.5.a / 25.A.7).
- 25.A.8 — Server must be grounded with at least one rear wheel in serving area; rear wheels must NOT contact court at serve; rear wheels must NOT be outside serving area at serve.
- 25.A.9 — **Two-bounce allowance**: wheelchair player may let ball bounce TWICE; second bounce can be anywhere on playing surface. Fault if not returned before third bounce.
- 25.A.10 — NVZ rules: front (smaller) wheels and rear stabilizing wheels MAY contact NVZ at any time. Large rear wheels may not contact NVZ during volley.
- 25.A.12.a — Transition standing↔wheelchair allowed once per match (treated as equipment time-out).

**25.B — Adaptive Standing (Change #25):**
- 25.B.3 — Eligibility-based two-bounce allowance for above-knee amputees, significant mobility impairments, neurological conditions (CP, stroke), users of crutches/braces. Must be declared before match.

**25.C — Hybrid Doubles (Change #25):**
- 25.C.1 — Each team = one wheelchair player + one standing player.
- 25.C.3 — Only eligible adaptive standing players may use two-bounce allowance in hybrid play.

---

## 25. COMMON PITFALLS & PROVEN-CORRECT CALLS

> **Pickle Rick's Top Ref/Player Pitfalls — Memorize These:**

1. **"My foot was on the NVZ line during my volley."** → FAULT (11.A.1). NVZ lines are part of the NVZ.
2. **"I volleyed; my momentum carried me into the kitchen after the ball was dead."** → FAULT (11.A.2). Momentum doesn't stop until you regain balance.
3. **"My partner was standing in NVZ during my volley with no contact between us."** → No fault. Partner's NVZ presence only matters if partner was IN CONTACT with you during the volley.
4. **"My hat fell off into the NVZ during a volley."** → FAULT (11.A.1) — anything in contact with the volleying player.
5. **"I called 'out' but the ball was clearly in."** → If you returned it, opponent gets the point (you stopped the rally; even if you returned, the call ends play). If you didn't return, your "out" call is the call (subject to opponent override per 8.G).
6. **"My partner and I disagreed on a line call."** → Ball is "in." (8.H — CHANGE #13 — "conflict" → in.)
7. **"I asked the spectator if it was in."** → 8.J — Spectators MUST NOT be consulted. Repeated → verbal/tech warning per 22.B.10.
8. **"Ball bounced in their court, then spin took it back to hit the net post."** → POINT for hitter (10.C.5 — Net Post Winner — CHANGE #2).
9. **"I called time-out silently with a finger."** → Tech warning per 21.A.2.b. Must be audible OR visible hand signal.
10. **"During my serve I added spin with my paddle at contact."** → LEGAL (7.B.2 — CHANGE #15). Spin via the paddle at contact is now allowed; spin via hand on release is still illegal.
11. **"Receiver was at game point in rally scoring; they won the rally on my serve."** → Receiver wins game (4.B, 14.A.2 — CHANGE #20).
12. **"I dropped my second ball during a rally."** → FAULT (24.B.1 — CHANGE #26).
13. **"My paddle face went over the net during my follow-through."** → LEGAL (13.I.1) IF you already hit the ball; ILLEGAL (13.I.1.a) if you crossed before contact.
14. **"Around-the-post (ATP) shot."** → LEGAL (13.C). Ball may go around outside the post; doesn't have to clear net height on the return path.
15. **"Ball hit the receiver's body before bouncing."** → If during a rally: FAULT on whoever was hit (10.C.3). If on a serve: FAULT on receiver (7.E.5) — point for server.
16. **"Volley serve where paddle head was at the same height as the wrist."** → If not CLEARLY above, it's legal (7.C.2). 2026 added "clearly" — benefit goes to server when ambiguous.
17. **"Player stopped a rally to challenge a CORRECT score."** → FAULT (6.F.2) on player who stopped.
18. **"Wheelchair player let ball bounce twice."** → LEGAL (25.A.9). Must return before third bounce.
19. **"Player carried/scooped the ball with their paddle."** → FAULT (12.C.1 — catch or carry).
20. **"During a volley, player's partner was touching them, and partner was standing in NVZ."** → FAULT (11.A.1) — anything in contact with the volleying player contacting NVZ counts.

---

## 26. RESPONSE FORMAT REQUIREMENTS

For EVERY answer Pickle Rick gives:
1. **Start with the most relevant 2026 rule citation** (e.g., "Rule 11.A.2 [Non-Volley Zone Momentum]" or "Rule 7.C.1 [Volley Serve – Upward Arc]"). Include the year if a 2025→2026 change applies (e.g., "Rule 8.H [2026 change — was 'doubt' under 6.C.8 in 2025]").
2. **If game context is missing** (rec vs. tournament, officiated vs. non-officiated, singles vs. doubles, standard vs. rally scoring) → ASK before ruling.
3. **If user references a 2025 rule number, map it to 2026 using Section 0.**
4. **Reference personal notes** when applicable. (No personal notes are loaded yet — placeholder for future.)
5. **End every response with:** "*Not official USAPA interpretation — confirm with a certified referee or tournament director if needed.*"
6. **For video questions:** First ask for transcription/key timestamps if you don't already have them. When analyzing frames, use "Frame N" format and cite the exact 2026 rule for each observed action.
"""


# =============================================================================
# SYSTEM PROMPTS — System prompts are concatenated with CORE_KNOWLEDGE on every call
# =============================================================================

# Verbatim custom instructions from the Project (with Pickle Rick brand)
PROJECT_INSTRUCTIONS = """You are Pickle Rick, a straightforward, hyper-precise USAPA pickleball rules assistant. You ONLY reference the uploaded documents (the 2026 USA Pickleball Official Rulebook and the 2026 Rulebook Change Document plus any personal notes loaded into CORE_KNOWLEDGE). Cite page/rule number every time. For video questions, first ask for transcription or key timestamps. Never hallucinate USAPA rules/cases/mechanics. Always ask clarifying questions on game context before ruling.

CRITICAL LAYERING RULE:
- The 2026 USA Pickleball Official Rulebook (effective January 1, 2026) is the AUTHORITATIVE source.
- The 2026 Rulebook Change Document explains every rule that changed from 2025 to 2026.
- If a player references a 2025 rule number, map it to the 2026 rule number using Section 0 of the CORE_KNOWLEDGE.
- Always cite using 2026 rule numbers as the primary reference. Note the 2025 → 2026 change number when relevant (e.g., "Change #15").
- Standard pickleball uses the rules as written; sanctioned tournament play modifies them via Sections 15–24 (e.g., a referee calls service foot faults under 19.A.1 / 20.E that players cannot enforce in non-officiated play).
- Wheelchair, adaptive standing, and hybrid doubles rules in Section 25 modify Sections 1–24 — apply the 25-series rules whenever relevant.

YOUR BEHAVIOR:
1. Start EVERY response with the most relevant 2026 rule citation (e.g., "Rule 11.A.2 [Non-Volley Zone Momentum]" or "Rule 7.C.1 [Volley Serve – Upward Arc]"). Include 2026 change # when a 2025→2026 change applies.
2. Reference personal notes when applicable (e.g., "From your 2025 pickup game notes…"). If no personal notes are loaded, skip this gracefully.
3. End EVERY response with: "*Not official USAPA interpretation — confirm with a certified referee or tournament director if needed.*"
4. Temperature = 0 mindset: maximum precision, no guessing, no hallucinating. If the rule is not in the CORE_KNOWLEDGE or attached files, say so plainly.
5. If game context is missing (rec vs. tournament, officiated vs. non-officiated, singles vs. doubles, standard vs. rally scoring, wheelchair/adaptive), ASK before ruling.
6. For video/film analysis: ALWAYS first ask for a transcription or key timestamps if you don't already have frame-level information. When you do analyze, use "Frame N" format and cite the exact 2026 rule for each observed action. Always include a VISIBILITY CHECK section.
7. Be straightforward. No filler. Cite, rule, disclaimer.
"""

# Main system prompt — used for chat + general Q&A
SYSTEM_PROMPT = f"""{PROJECT_INSTRUCTIONS}

---

{CORE_KNOWLEDGE}
"""

# Video-analysis system prompt — adds video-specific output structure
VIDEO_SYSTEM_PROMPT = f"""{PROJECT_INSTRUCTIONS}

VIDEO ANALYSIS OUTPUT STRUCTURE — use this exact structure when analyzing pickleball video frames:

## 🎬 Pickle Rick Video Analysis
**Clip:** [filename] | **Frames:** [range] | **Date:** [today]

## 👁️ Visibility Check
For each key element (server, receiver, NVZ line, baseline, ball flight, paddle contact point), note: CLEARLY VISIBLE (frames N…) / PARTIALLY VISIBLE / NOT VISIBLE.

## 📋 Play-by-Play (Frame-by-Frame)
Walk through the sequence with rule citations on every observation. Use "Frame N" format.

## ⚠️ Faults & Violations Detected
List every fault observed with the EXACT 2026 rule number (e.g., "Rule 11.A.1 — NVZ Contact While Volleying — Frame 4: server's left foot clearly on NVZ line during volley").

## ✅ Correct Calls / Legal Plays
Confirm what was within the rules.

## 🤔 Inconclusive
List anything you can't rule on definitively due to camera angle, frame rate, or visibility.

## 📝 Summary
Concise ruling: who wins the rally and why, citing the deciding rule.

---
*Not official USAPA interpretation — confirm with a certified referee or tournament director if needed.*

{CORE_KNOWLEDGE}
"""

# Quiz system prompt — strict JSON output for quiz generator
QUIZ_SYSTEM_PROMPT = f"""You are Pickle Rick Quiz Engine — a precise question generator for USA Pickleball players and referees, based EXCLUSIVELY on the 2026 USA Pickleball Official Rulebook + 2026 Rulebook Change Document.

ABSOLUTE RULES — violating these will cause failures:
1. Respond with ONLY valid JSON. Zero preamble. Zero markdown fences. Zero trailing text.
2. Multiple-choice: EXACTLY 4 options (A, B, C, D). Exactly ONE correct answer.
3. True/False: EXACTLY 2 options: {{"A": "True", "B": "False"}}.
4. Mix types roughly 50% multiple_choice / 50% true_false.
5. Questions must be CHALLENGING. Use specific 2026 rule numbers and realistic scenarios.
6. NEVER repeat the same topic, scenario, or rule in a batch. Cover wide breadth.
7. Distractors for MC must be plausible but clearly wrong to a careful student.

Single question JSON structure:
{{
  "question": "Full question text — be specific and scenario-based when possible",
  "type": "multiple_choice",
  "options": {{"A": "option", "B": "option", "C": "option", "D": "option"}},
  "correct": "B",
  "explanation": "Thorough explanation: why correct answer is right, why each wrong answer is wrong, what the 2026 rule actually says.",
  "rule_citation": "Exact 2026 rule number (e.g. 'Rule 11.A.2' or 'Rule 7.C.1, 2026 Change #23')",
  "personal_note": "",
  "topic": "Serving|NVZ|Line Calls|Scoring|Faults|Tournament|2026 Changes|Wheelchair|Mechanics|Conduct"
}}

True/False structure:
{{
  "question": "True or False: [specific statement]",
  "type": "true_false",
  "options": {{"A": "True", "B": "False"}},
  "correct": "A",
  "explanation": "...",
  "rule_citation": "...",
  "personal_note": "",
  "topic": "..."
}}

For a BATCH of 10 questions: JSON array of 10 objects. Include:
- At least 2 questions on 2026 changes (rally scoring receiver wins, paddle spin on serve, net post winner, conflict→in, audible time-out, etc.)
- At least 2 NVZ questions (Section 11)
- At least 2 serving questions (Section 7 — volley vs drop serve, foot faults, spin)
- At least 1 line-call question (Section 8 / Section 19)
- At least 1 scoring question (Section 4 / Section 14)
- At least 1 conduct/tech foul question (Section 22)
- The rest from elsewhere — vary breadth

{CORE_KNOWLEDGE}
"""


# =============================================================================
# PAGE CONFIG
# =============================================================================

# Resolve logo path: prefer same-directory file, fall back to /mnt or skip.
_LOGO_CANDIDATES = [
    Path(__file__).parent / "picklerick_logo.jpg" if "__file__" in globals() else None,
    Path("picklerick_logo.jpg"),
    Path("/mnt/user-data/uploads/IMG_0581.JPG"),
    Path("IMG_0581.JPG"),
]
LOGO_PATH = next((str(p) for p in _LOGO_CANDIDATES if p and p.exists()), None)

st.set_page_config(
    page_title="Pickle Rick — Your Pickleball Rules Assistant",
    page_icon=LOGO_PATH if LOGO_PATH else "🥒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# THEME — Creme background, black text, vibrant pickle-green + court-blue accents
# =============================================================================

# Pulled directly from the Pickle Rick logo:
GREEN       = "#22C55E"   # Bright pickle green — primary accent
GREEN_DARK  = "#15803D"   # Deeper pickle green — header/text accent
GREEN_LIGHT = "#4ADE80"   # Light pickle green — hover/highlight
BLUE        = "#1E56A0"   # Court / paddle blue — secondary accent
BLUE_LIGHT  = "#60A5FA"
CREAM       = "#F5F5DC"   # Spec'd creme background
CARD        = "#FFFFFF"
BORDER      = "#E5E7CB"   # Soft creme border
TEXT        = "#1F2937"   # Black-ish for body text
MUTED       = "#4B5563"
AMBER       = "#92400E"
RED         = "#991B1B"

# Subtle pickleball-court-inspired SVG background pattern
_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'>"
    "<rect width='140' height='140' fill='none'/>"
    # Court sidelines
    "<line x1='0' y1='70' x2='140' y2='70' stroke='%2322C55E' stroke-width='0.4' opacity='0.10'/>"
    "<line x1='70' y1='0' x2='70' y2='140' stroke='%2322C55E' stroke-width='0.4' opacity='0.10'/>"
    # NVZ rectangle suggestion
    "<rect x='40' y='55' width='60' height='30' fill='none' stroke='%231E56A0' stroke-width='0.35' opacity='0.07'/>"
    # Pickleball with holes
    "<circle cx='70' cy='70' r='6' fill='none' stroke='%2322C55E' stroke-width='0.5' opacity='0.13'/>"
    "<circle cx='68' cy='68' r='0.5' fill='%2322C55E' opacity='0.20'/>"
    "<circle cx='72' cy='68' r='0.5' fill='%2322C55E' opacity='0.20'/>"
    "<circle cx='70' cy='72' r='0.5' fill='%2322C55E' opacity='0.20'/>"
    "</svg>"
)
BG_URL = "data:image/svg+xml," + urllib.parse.quote(_SVG)

# ── CSS Layer 1: Buttons, selectbox, sidebar, dark text ──────────────────────
st.markdown(f"""
<style>
    /* Buttons — creme bg, green border, dark text */
    .stButton button, button, .stButton>button {{
        color: {TEXT} !important;
        background-color: #FAFAF0 !important;
        border: 2px solid {GREEN_DARK} !important;
        font-weight: 600;
    }}
    .stButton button:hover {{
        background-color: {GREEN_LIGHT} !important;
        border-color: {GREEN_DARK} !important;
        color: {TEXT} !important;
    }}
    .stButton button:disabled, .stButton>button:disabled {{
        background-color: #F1F5F1 !important;
        color: #94A3B8 !important;
        border-color: #94A3B8 !important;
    }}
    /* Download buttons stand out a tad */
    .stDownloadButton button {{
        border-color: {BLUE} !important;
    }}
    /* Selectbox + multiselect */
    .stSelectbox > div, .stMultiSelect > div,
    .stSelectbox > div > div, .stMultiSelect > div > div {{
        color: {TEXT} !important;
        background-color: #FAFAF0 !important;
        border: 2px solid {GREEN_DARK} !important;
    }}
    .stSelectbox label, .stMultiSelect label,
    [data-baseweb="select"] span, [data-baseweb="select"] div,
    [data-baseweb="popover"] li, [data-baseweb="menu"] li {{
        color: {TEXT} !important;
        background-color: #FAFAF0 !important;
    }}
    /* Sidebar */
    [data-testid="stSidebar"] {{ background-color: {CARD} !important; }}
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stTextInput,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{ color: {TEXT} !important; }}
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] span {{
        color: {TEXT} !important; background-color: #FAFAF0 !important;
    }}
    /* Tabs */
    .stTabs [data-baseweb="tab"] {{ color: {TEXT} !important; }}
    .stTabs [aria-selected="true"] {{
        color: {GREEN_DARK} !important;
        border-bottom: 3px solid {GREEN} !important;
    }}
    /* Dark text everywhere */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
    .stMarkdown span, .stMarkdown strong, .stMarkdown em,
    p, span, label, h1, h2, h3, h4, h5,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] span,
    .stChatMessage p, .stChatMessage span, .stChatMessage li,
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] span,
    [data-testid="stChatMessageContent"] li {{ color: {TEXT} !important; }}
</style>
""", unsafe_allow_html=True)

# ── CSS Layer 2: Inputs, alerts, expanders ────────────────────────────────────
st.markdown(f"""
<style>
.stRadio label, .stRadio label span, .stRadio label p,
div[data-testid="stRadio"] label span,
div[data-testid="stRadio"] label p,
.stRadio > div > label > div > p {{
    color: {TEXT} !important;
    font-size: 0.95rem !important;
}}
.stChatInput textarea, .stChatInput input {{
    color: {TEXT} !important; background-color: #FFFFFF !important;
}}
.stTextArea textarea, .stTextInput input {{
    color: {TEXT} !important; background-color: #FFFFFF !important;
}}
[data-baseweb="select"] span, [data-baseweb="select"] div {{ color: {TEXT} !important; }}
.stAlert p, .stAlert span, .stAlert div {{ color: {TEXT} !important; }}
.streamlit-expanderHeader p, .streamlit-expanderHeader span {{ color: {GREEN_DARK} !important; }}
.stCaption, .stCaption p {{ color: {MUTED} !important; }}
</style>
""", unsafe_allow_html=True)

# ── CSS Layer 3: Full theme styling ───────────────────────────────────────────
st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    background-color: {CREAM};
    background-image: url("{BG_URL}");
    background-repeat: repeat;
    color: {TEXT};
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}
.main .block-container {{ background: transparent; padding-top: 0.5rem; max-width: 1100px; }}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {CARD}; border-right: 2px solid {GREEN_DARK};
    box-shadow: 2px 0 8px rgba(34,197,94,0.10);
}}

/* Hero header */
.pr-hero {{ text-align: center; padding: 1.5rem 1.5rem 1.0rem 1.5rem; }}
.pr-hero-title {{
    color: {GREEN_DARK} !important; font-size: 2.8rem; font-weight: 900;
    letter-spacing: -1.0px; margin: 0.6rem 0 0.2rem 0; line-height: 1.1;
    text-shadow: 1px 1px 0 rgba(0,0,0,0.05);
}}
.pr-hero-slogan {{ color: {MUTED}; font-size: 1.05rem; font-weight: 500; margin: 0 0 1.2rem 0; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {CARD}; border-bottom: 2px solid {GREEN_DARK};
    border-radius: 8px 8px 0 0; gap: 2px; padding: 0 0.4rem;
}}
.stTabs [data-baseweb="tab"] {{
    color: {MUTED} !important; font-weight: 600; font-size: 0.95rem;
    padding: 0.55rem 1rem; border-radius: 6px 6px 0 0;
}}
.stTabs [aria-selected="true"] {{
    color: {GREEN_DARK} !important; background-color: {CREAM} !important;
    border-bottom: 3px solid {GREEN} !important;
}}

/* Cards */
.pr-card {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 1.2rem 1.4rem; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(34,197,94,0.06); color: {TEXT};
}}
.pr-card-green {{
    background: {CARD}; border-left: 4px solid {GREEN};
    border-radius: 0 10px 10px 0; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    box-shadow: 0 2px 8px rgba(34,197,94,0.08); color: {TEXT};
}}
.pr-card-blue {{
    background: {CARD}; border-left: 4px solid {BLUE};
    border-radius: 0 10px 10px 0; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    box-shadow: 0 2px 8px rgba(30,86,160,0.08); color: {TEXT};
}}

/* Quiz cards */
.quiz-question-card {{
    background: {CARD}; border: 2px solid {BORDER}; border-radius: 12px;
    padding: 1.5rem 1.8rem; margin-bottom: 1rem;
    box-shadow: 0 3px 12px rgba(34,197,94,0.10); color: {TEXT};
}}
.quiz-question-text {{
    font-size: 1.05rem; font-weight: 600; color: {TEXT} !important;
    line-height: 1.55; margin-bottom: 0.5rem;
}}
.quiz-result-correct {{
    background: #F0FDF4; border: 2px solid {GREEN}; border-radius: 8px;
    padding: 1rem 1.2rem; margin-top: 0.8rem; color: #14532D !important;
}}
.quiz-result-wrong {{
    background: #FFF1F2; border: 2px solid #F87171; border-radius: 8px;
    padding: 1rem 1.2rem; margin-top: 0.8rem; color: #7F1D1D !important;
}}
.quiz-explanation {{
    background: #ECFDF5; border-left: 4px solid {GREEN}; border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem; margin-top: 0.8rem; font-size: 0.92rem;
    line-height: 1.65; color: {TEXT} !important;
}}

/* Pills */
.pill-ok {{
    display: inline-block; background: #DCFCE7; color: {GREEN_DARK};
    font-weight: 700; font-size: 0.78rem; border-radius: 20px;
    padding: 2px 10px; border: 1px solid {GREEN};
}}
.pill-warn {{
    display: inline-block; background: #FEF3C7; color: {AMBER};
    font-weight: 700; font-size: 0.78rem; border-radius: 20px;
    padding: 2px 10px; border: 1px solid #FCD34D;
}}
.pill-err {{
    display: inline-block; background: #FEE2E2; color: #991B1B;
    font-weight: 700; font-size: 0.78rem; border-radius: 20px;
    padding: 2px 10px; border: 1px solid #F87171;
}}
.pill-blue {{
    display: inline-block; background: #DBEAFE; color: {BLUE};
    font-weight: 700; font-size: 0.78rem; border-radius: 20px;
    padding: 2px 10px; border: 1px solid {BLUE_LIGHT};
}}
.pill-green {{
    display: inline-block; background: #DCFCE7; color: {GREEN_DARK};
    font-weight: 700; font-size: 0.78rem; border-radius: 20px;
    padding: 2px 10px; border: 1px solid {GREEN};
}}

/* Misc */
.streamlit-expanderHeader {{
    background-color: #ECFDF5 !important; color: {GREEN_DARK} !important;
    font-weight: 600 !important; border-radius: 8px !important;
}}
.pr-footer {{
    text-align: center; color: {MUTED}; font-size: 0.78rem;
    border-top: 1px solid {BORDER}; padding-top: 1rem; margin-top: 2.5rem;
}}
.pickle-log-card {{
    background: #ECFDF5; border: 1px solid {GREEN};
    border-left: 4px solid {GREEN_DARK}; border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.1rem; font-size: 0.88rem; color: {TEXT};
}}
#MainMenu {{ display: none !important; }}
[data-testid="stMainMenu"] {{ display: none !important; }}
footer {{ visibility: hidden; }}
[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stAppDeployButton"], .stAppDeployButton {{ display: none !important; }}
[data-testid="stToolbarActions"] > *:nth-child(n+2) {{ display: none !important; }}
[data-baseweb="select"] {{ background-color: {CARD} !important; }}
.stAlert {{ border-radius: 8px !important; font-size: 0.88rem !important; }}

/* Inputs / file uploader */
.stTextArea textarea, .stTextInput input {{
    background-color: {CARD} !important; color: {TEXT} !important;
    border: 1.5px solid {BORDER} !important; border-radius: 8px !important;
    font-size: 0.92rem !important;
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
    border-color: {GREEN} !important; box-shadow: 0 0 0 3px rgba(34,197,94,0.15) !important;
}}
[data-testid="stFileUploader"] {{
    border: 2px dashed {GREEN} !important; border-radius: 10px !important;
    background-color: #F0FDF4 !important; padding: 0.5rem;
}}
.stChatMessage {{
    background: {CARD} !important; border: 1px solid {BORDER} !important;
    border-radius: 10px !important; margin-bottom: 0.5rem;
    box-shadow: 0 1px 4px rgba(34,197,94,0.07);
}}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def _s(key, default):
    """Initialize a session state key with a default if not set."""
    if key not in st.session_state:
        st.session_state[key] = default

# Chat
_s("messages", [])
_s("uploaded_files_content", [])
_s("api_key", "")
_s("model_choice", "claude-sonnet-4-6")

# Video Analyzer
_s("va_frames", [])
_s("va_frame_count", 0)
_s("va_video_name", "")
_s("va_fps_used", 1.0)
_s("va_analysis_result", "")

# Quiz
_s("quiz_mode", None)            # None | "single" | "ten"
_s("quiz_topic", "Mixed")
_s("quiz_current_q", None)
_s("quiz_answered", False)
_s("quiz_user_answer", None)
_s("quiz_total", 0)
_s("quiz_correct", 0)
_s("quiz_session_topics", [])
_s("tenq_questions", [])
_s("tenq_index", 0)
_s("tenq_answers", [])
_s("tenq_finished", False)
_s("tenq_answered_this", False)
_s("tenq_user_answer", None)
_s("quiz_log", [])


# =============================================================================
# HELPERS — Anthropic API client
# =============================================================================

def b64(data: bytes) -> str:
    """Base64-encode bytes for API transmission."""
    return base64.standard_b64encode(data).decode("utf-8")


def get_api_key() -> str | None:
    """
    Resolve the Anthropic API key. Checks sidebar input, secrets, and env
    var first; falls back to the hardcoded key so the app always works.
    """
    _HARDCODED = (
        "sk-ant-api03-iQN6qoXOjRUOfuX-746v76UjNhy8_2CoNyAJ2AhL1l04"
        "E5JmueUi5kZsewxd1sgnw9bg2XtLcpeULxhf6EGoOQ-DqwEmAAA"
    )
    if st.session_state.get("api_key"):
        return st.session_state.api_key
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    try:
        return st.secrets["anthropic"]["api_key"]
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key
    return _HARDCODED


def make_client():
    """Create an Anthropic client. Stops the app gracefully if key missing."""
    key = get_api_key()
    if not key:
        st.error(
            "❌ **Anthropic API key not found.**\n\n"
            "Add it in the sidebar, or via `.streamlit/secrets.toml`:\n```\n"
            'ANTHROPIC_API_KEY = "sk-ant-..."\n```'
        )
        st.stop()
    return anthropic.Anthropic(api_key=key)


def api_key_ok() -> bool:
    """Check whether an API key is available (without making a call)."""
    return bool(get_api_key())


def handle_api_error(e: Exception) -> str:
    """Convert API exceptions to friendly messages."""
    if isinstance(e, anthropic.AuthenticationError):
        return "❌ Authentication failed. Check your Anthropic API key."
    if isinstance(e, anthropic.RateLimitError):
        return "⚠️ Rate limit reached. Wait a moment and try again."
    if isinstance(e, anthropic.APIConnectionError):
        return "❌ Connection error. Check your internet connection."
    if isinstance(e, anthropic.BadRequestError):
        return (f"❌ Request too large or malformed: {e}\n\n"
                "Try fewer frames or a smaller upload.")
    return f"❌ Unexpected error: {e}"


def prepare_file_content(uf):
    """
    Convert a Streamlit-uploaded file into an Anthropic API content block.
    Supports PDFs (native document blocks), JPG/PNG images, and TXT.
    Videos are handled separately via the Video Analyzer tab.
    """
    data = uf.read()
    name = uf.name.lower()
    if name.endswith(".pdf"):
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64(data),
            },
            "title": uf.name,
        }
    if name.endswith((".jpg", ".jpeg")):
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(data)},
        }
    if name.endswith(".png"):
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64(data)},
        }
    if name.endswith(".txt"):
        return {
            "type": "text",
            "text": f"[File: {uf.name}]\n\n{data.decode('utf-8', errors='replace')}",
        }
    return None


def stream_chat(client, messages, files, system=None):
    """
    Stream a chat response. The most-recent user message is augmented with any
    uploaded file blocks (PDFs/images/text) so the model can reference them.
    """
    sys_p = system or SYSTEM_PROMPT
    api_msgs = []
    for i, m in enumerate(messages):
        if m["role"] == "user" and i == len(messages) - 1 and files:
            blocks = list(files) + [{"type": "text", "text": m["content"]}]
            api_msgs.append({"role": "user", "content": blocks})
        else:
            api_msgs.append({"role": m["role"], "content": m["content"]})
    with client.messages.stream(
        model=st.session_state.model_choice,
        max_tokens=4096,
        system=sys_p,
        messages=api_msgs,
        temperature=0,
    ) as s:
        yield from s.text_stream


def call_api_sync(prompt: str, system: str, max_tokens: int = 3000) -> str:
    """Synchronous (non-streaming) API call — used for quiz generation."""
    client = make_client()
    resp = client.messages.create(
        model=st.session_state.model_choice,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.content[0].text


def chat_log_json() -> str:
    """Serialize the current chat as JSON for export."""
    return json.dumps({
        "exported_at": datetime.datetime.now().isoformat(),
        "app": "Pickle Rick — USAPA Pickleball Rules Assistant",
        "model": st.session_state.model_choice,
        "messages": [
            {
                "role": m["role"],
                "content": m["content"],
                "timestamp": m.get("timestamp", ""),
            }
            for m in st.session_state.messages
        ],
    }, indent=2, ensure_ascii=False)


# =============================================================================
# HELPERS — Video frame extraction (OpenCV)
# =============================================================================

def extract_frames(video_path: str, fps: float = 1.0) -> list:
    """Extract frames from a video at the specified fps. Returns list of base64 JPEGs."""
    if not OPENCV_AVAILABLE:
        raise RuntimeError("opencv-python-headless not available.")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    interval = max(1, int(round(native_fps / fps)))
    frames, idx = [], 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % interval == 0:
            h, w = frame.shape[:2]
            # Cap width at 1280 to keep request size manageable
            if w > 1280:
                frame = cv2.resize(frame, (1280, int(h * 1280 / w)),
                                   interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                frames.append(base64.standard_b64encode(buf).decode("utf-8"))
        idx += 1
    cap.release()
    return frames


def build_vision_content(frames_b64, start_idx, end_idx, user_question,
                         video_name, fps_used, preamble_extra="") -> list:
    """Build the Anthropic content blocks for vision analysis (interleaved frames)."""
    selected = frames_b64[start_idx: end_idx + 1]
    spf = 1.0 / fps_used
    content = [{
        "type": "text",
        "text": (
            f"Pickleball clip: {video_name}\n"
            f"Frames: {len(selected)} ({start_idx + 1}–{end_idx + 1} "
            f"of {len(frames_b64)}) at {fps_used} fps ({spf:.1f}s/frame).\n"
            f"Frame numbering is 1-based. Use 'Frame N' format throughout your reply.\n"
            f"{preamble_extra}\n"
        ),
    }]
    for i, fb in enumerate(selected):
        fn = start_idx + i + 1
        content.append({"type": "text",
                        "text": f"--- Frame {fn} (~{(fn - 1) / fps_used:.1f}s) ---"})
        content.append({"type": "image",
                        "source": {"type": "base64",
                                   "media_type": "image/jpeg",
                                   "data": fb}})
    content.append({"type": "text", "text": f"\nQuestion / Context:\n{user_question}"})
    return content


def stream_vision(client, content_blocks, system):
    """Stream a vision response from Claude given frame-rich content."""
    with client.messages.stream(
        model=st.session_state.model_choice,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": content_blocks}],
        temperature=0,
    ) as s:
        yield from s.text_stream


# =============================================================================
# HELPERS — Quiz engine
# =============================================================================

def _strip_json_fences(raw: str) -> str:
    """Strip ```json fences if Claude added them despite system prompt."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def generate_single_question(topic: str, used_topics: list = None) -> dict | None:
    """Generate ONE quiz question via the API. Returns dict or None on failure."""
    if not api_key_ok():
        st.error("❌ Add your API key in the sidebar to generate questions.")
        return None
    avoid_str = ""
    if used_topics:
        recent = used_topics[-5:]
        avoid_str = (f"IMPORTANT: Do NOT generate a question on any of these "
                     f"recently asked topics: {', '.join(recent)}. "
                     "Pick a totally different rule, scenario, or section.\n")
    import random
    q_type = "true_false" if random.random() < 0.5 else "multiple_choice"
    topic_str = "" if topic == "Mixed" else f"Topic focus: {topic}. "
    prompt = (
        f"{avoid_str}"
        f"{topic_str}"
        f"Generate one {q_type} question for a USA Pickleball player or referee "
        f"based on the 2026 Rulebook. Reference EXACT 2026 rule numbers. "
        f"For multiple_choice: EXACTLY 4 options (A, B, C, D). "
        f"For true_false: EXACTLY 2 options (A=True, B=False). "
        f"Respond with ONLY valid JSON — no fences, no preamble."
    )
    try:
        raw = _strip_json_fences(call_api_sync(prompt, QUIZ_SYSTEM_PROMPT, max_tokens=900))
        q = json.loads(raw)
        if q.get("type") == "multiple_choice" and len(q.get("options", {})) != 4:
            return None
        if q.get("type") == "true_false" and len(q.get("options", {})) != 2:
            return None
        return q
    except Exception as e:
        st.error(f"❌ Failed to generate question: {e}")
        return None


def generate_ten_questions(topic: str) -> list | None:
    """Generate a 10-question quiz batch. Returns list[dict] or None on failure."""
    if not api_key_ok():
        st.error("❌ Add your API key in the sidebar to generate quizzes.")
        return None
    topic_str = "" if topic == "Mixed" else f"Topic focus: {topic}. "
    prompt = (
        f"{topic_str}Generate exactly 10 questions for a USA Pickleball player/ref. "
        "Mix: 5 multiple_choice (EXACTLY 4 options A/B/C/D each) + 5 true_false. "
        "Cover these 2026 areas: rally scoring receiver-wins (4.B, 14.A.2), "
        "spin via paddle on serve (7.B.2), volley serve 'clearly' rule (7.C), "
        "NVZ momentum (11.A.2), partner conflict→in (8.H), net post winner (10.C.5), "
        "audible time-out (21.A.2), spectators not consulted (8.J), extra ball fault (24.B.1), "
        "wheelchair two-bounce (25.A.9). "
        "Respond with ONLY a valid JSON ARRAY of 10 objects — no fences, no preamble."
    )
    try:
        raw = _strip_json_fences(call_api_sync(prompt, QUIZ_SYSTEM_PROMPT, max_tokens=6000))
        questions = json.loads(raw)
        if isinstance(questions, list) and len(questions) >= 5:
            return questions[:10]
        st.error("❌ Unexpected question count. Try again.")
        return None
    except Exception as e:
        st.error(f"❌ Failed to generate quiz: {e}")
        return None


def render_question_card(q: dict, question_num: str = ""):
    """Render a single quiz question card."""
    q_text = q.get("question", "")
    q_type = q.get("type", "multiple_choice")
    badge_label = "True/False" if q_type == "true_false" else "Multiple Choice"
    st.markdown(f"""
    <div class="quiz-question-card">
        <div class="quiz-question-text">{question_num} {q_text}
        <span style="background:#DCFCE7;color:{GREEN_DARK};font-size:0.72rem;
        font-weight:700;border-radius:20px;padding:2px 8px;margin-left:8px;">
        {badge_label}</span></div>
    </div>
    """, unsafe_allow_html=True)


def render_feedback(q: dict, user_answer: str) -> bool:
    """Render the correct/incorrect feedback + explanation."""
    correct = q.get("correct", "")
    options = q.get("options", {})
    correct_text = options.get(correct, correct)
    user_text = options.get(user_answer, user_answer)
    is_correct = user_answer == correct
    if is_correct:
        st.markdown(f"""<div class="quiz-result-correct">
        <strong>✅ Correct!</strong> &nbsp; {user_answer}: {user_text}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="quiz-result-wrong">
        <strong>❌ Incorrect.</strong> You chose: {user_answer}: {user_text}<br>
        <strong>✔ Correct: {correct}: {correct_text}</strong>
        </div>""", unsafe_allow_html=True)
    explanation = q.get("explanation", "")
    rule_cite = q.get("rule_citation", "")
    personal = q.get("personal_note", "")
    pnote = f'<br><strong>📋 From your notes:</strong> {personal}' if personal else ""
    st.markdown(f"""<div class="quiz-explanation">
    <strong>📖 Explanation</strong><br>{explanation}<br><br>
    <strong>📌 Citation:</strong> {rule_cite}{pnote}
    </div>""", unsafe_allow_html=True)
    return is_correct


def accuracy_display(correct: int, total: int):
    """Show a small accuracy bar."""
    pct = int(round(correct / total * 100)) if total > 0 else 0
    color = GREEN_DARK if pct >= 80 else (AMBER if pct >= 60 else RED)
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;background:{CARD};
                border:1px solid {BORDER};border-radius:8px;padding:0.7rem 1rem;
                margin-bottom:0.8rem;">
        <div style="font-weight:800;font-size:1.4rem;color:{color};min-width:52px;">{pct}%</div>
        <div style="flex:1;">
            <div style="background:#E2E8F0;border-radius:20px;height:10px;margin:6px 0 2px 0;overflow:hidden;">
                <div style="height:10px;border-radius:20px;width:{pct}%;background:{color};"></div>
            </div>
            <div style="font-size:0.8rem;color:{MUTED};margin-top:3px;">
                {correct} correct of {total} answered</div>
        </div>
    </div>""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    # Sidebar logo
    if LOGO_PATH:
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown(
            f'<div style="text-align:center;font-size:3rem;margin-bottom:0.5rem;">🥒</div>',
            unsafe_allow_html=True,
        )

    # API key is hardcoded — show silent status only
    st.markdown('<span class="pill-ok">✅ API key loaded</span>', unsafe_allow_html=True)
    st.caption("Powered by Anthropic · claude-sonnet-4-6")

    st.markdown("---")

    # Knowledge base status
    st.markdown("**📚 Knowledge Base**")
    st.markdown(
        '<span class="pill-green">✅ Core Knowledge Loaded</span>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Pickleball rules AI assistant trained on USAPA rulebook and all "
        "recent updates."
    )

    st.markdown("---")

    # File uploader
    st.markdown("**📎 Upload Files** *(home chat)*")
    st.caption("PDFs, images (JPG/PNG), TXT. Videos use the Video Analyzer tab.")
    chat_uploads = st.file_uploader(
        "chatfiles",
        type=["pdf", "jpg", "jpeg", "png", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if chat_uploads:
        proc, names = [], []
        for uf in chat_uploads:
            blk = prepare_file_content(uf)
            if blk:
                proc.append(blk); names.append(uf.name)
            else:
                st.warning(f"Unsupported: {uf.name}")
        st.session_state.uploaded_files_content = proc
        if names:
            st.markdown(f'<span class="pill-ok">✅ {len(names)} file(s) loaded</span>',
                        unsafe_allow_html=True)
    else:
        st.session_state.uploaded_files_content = []

    st.markdown("---")

    # Pickle Log (chat log download)
    st.markdown("**📒 Pickle Log**")
    if st.session_state.messages:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "⬇️ Download Chat Log (JSON)",
            data=chat_log_json(),
            file_name=f"picklerick_chat_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.caption("Chat log appears here after your first message.")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# =============================================================================
# HEADER (logo + title)
# =============================================================================

# Center the logo
logo_col_l, logo_col_c, logo_col_r = st.columns([2, 3, 2])
with logo_col_c:
    if LOGO_PATH:
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown(
            f"<div style='text-align:center;font-size:5rem;'>🥒</div>",
            unsafe_allow_html=True,
        )

st.markdown(f"""
<div class="pr-hero">
    <div class="pr-hero-title">Pickle Rick</div>
    <div class="pr-hero-slogan">Your Pickleball Rules Assistant — USAPA-trained, ref-grade precision.</div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# TABS
# =============================================================================

tab_home, tab_video, tab_quiz = st.tabs([
    "🥒 Home / Chat",
    "🎬 Video Analyzer",
    "📝 Quiz",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — HOME / CHAT
# ─────────────────────────────────────────────────────────────────────────────

with tab_home:
    # Topic chips
    chips = [
        "2026 Rule Citations", "Non-Volley Zone", "Serve Rules", "Line Calls",
        "Rally Scoring", "Tournament Conduct", "Wheelchair Play",
    ]
    chip_html = " &nbsp; ".join(f'<span class="pill-green">{c}</span>' for c in chips)
    st.markdown(f'<div style="text-align:center;margin-bottom:1.4rem;line-height:2.6;">'
                f'{chip_html}</div>', unsafe_allow_html=True)

    # Quick-start prompts (only shown when no messages yet)
    if not st.session_state.messages:
        st.markdown(
            f'<p style="text-align:center;color:{MUTED};font-size:0.92rem;'
            f'margin-bottom:0.8rem;"><em>Try one of these or type your own below</em></p>',
            unsafe_allow_html=True,
        )
        starter_qs = [
            "What changed in 2026 for the volley serve? Cite the rule.",
            "My partner and I disagreed on a line call — what's the call in 2026?",
            "Can I add spin to the ball with my paddle on the serve?",
            "Ball bounced in our court, then spin took it back into the net post — who wins?",
            "Walk me through NVZ momentum faults with a worst-case example.",
            "In rally scoring, can the receiving team win on game point?",
            "What are the 2026 rule changes I most need to know?",
            "How does the wheelchair two-bounce allowance work?",
        ]
        c1, c2 = st.columns(2)
        for i, q in enumerate(starter_qs):
            col = c1 if i < 4 else c2
            with col:
                if st.button(f"➤ {q}", key=f"hq_{i}", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user", "content": q,
                        "timestamp": datetime.datetime.now().isoformat(),
                    })
                    st.rerun()

    # Render chat history
    for msg in st.session_state.messages:
        avatar = "🥒" if msg["role"] == "user" else "⚡"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Stream assistant reply if last message is from user
    if (st.session_state.messages
            and st.session_state.messages[-1]["role"] == "user"):
        if not api_key_ok():
            st.warning("⚠️ Enter your Anthropic API key in the sidebar to get a reply.")
        else:
            client = make_client()
            with st.chat_message("assistant", avatar="⚡"):
                ph = st.empty()
                full = ""
                try:
                    with st.spinner("Pickle Rick is checking the rulebook…"):
                        for chunk in stream_chat(
                            client,
                            st.session_state.messages,
                            st.session_state.uploaded_files_content,
                        ):
                            full += chunk
                            ph.markdown(full + "▌")
                    ph.markdown(full)
                    st.session_state.messages.append({
                        "role": "assistant", "content": full,
                        "timestamp": datetime.datetime.now().isoformat(),
                    })
                except Exception as e:
                    st.error(handle_api_error(e))

    # Chat input pinned to bottom
    user_in = st.chat_input(
        "Ask anything about USAPA pickleball rules, NVZ, serves, line calls, scoring…",
    )
    if user_in:
        st.session_state.messages.append({
            "role": "user", "content": user_in,
            "timestamp": datetime.datetime.now().isoformat(),
        })
        st.rerun()

    # Pickle Log expander (session summary)
    if st.session_state.messages:
        st.markdown("---")
        with st.expander("📒 Pickle Log — Session Summary", expanded=False):
            st.markdown(f"""<div class="pickle-log-card">
            <strong>Session Stats</strong><br>
            Messages: {len(st.session_state.messages)} &nbsp;|&nbsp;
            Model: {st.session_state.model_choice}<br>
            Started: {st.session_state.messages[0].get("timestamp", "")[:19]}<br>
            Last: {st.session_state.messages[-1].get("timestamp", "")[:19]}
            </div>""", unsafe_allow_html=True)
            for i, m in enumerate(st.session_state.messages):
                icon = "🥒 You" if m["role"] == "user" else "⚡ Pickle Rick"
                st.markdown(f"**{icon}** _{m.get('timestamp', '')[:19]}_")
                st.markdown(m["content"])
                if i < len(st.session_state.messages) - 1:
                    st.markdown("---")
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "⬇️ Save Pickle Log",
                data=chat_log_json(),
                file_name=f"picklerick_picklelog_{ts}.json",
                mime="application/json",
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — VIDEO ANALYZER (consolidated single tab — pickleball video only)
# ─────────────────────────────────────────────────────────────────────────────

with tab_video:
    st.markdown("## 🎬 Video Analyzer")
    st.markdown(
        "Upload a pickleball clip. Pickle Rick extracts frames with OpenCV "
        "and analyzes them for rule-based feedback: serves, NVZ violations, "
        "line calls, faults, and more — citing exact 2026 rule numbers."
    )

    if not OPENCV_AVAILABLE:
        st.error(
            "**opencv-python-headless is not installed.** Run:\n\n"
            "`pip install opencv-python-headless`\n\nThen restart the app."
        )
    else:
        st.markdown("### Step 1 — Upload Clip")
        st.info("Keep clips to 10–60 seconds for best results. Trim to the specific play.")
        va_vid = st.file_uploader(
            "videofile", type=["mp4", "mov"],
            label_visibility="collapsed", key="va_uploader",
        )

        if va_vid:
            st.markdown("### Step 2 — Extraction Settings")
            fc1, fc2 = st.columns([1, 2])
            with fc1:
                fps_c = st.select_slider(
                    "fps_va", options=[0.5, 1.0, 2.0], value=1.0,
                    help="0.5 = overview | 1.0 = standard | 2.0 = fast action",
                    key="va_fps",
                )
                st.caption(f"30s clip at {fps_c} fps ≈ {int(30 * fps_c)} frames")
            with fc2:
                st.info("Each frame ≈ 800–1,600 tokens. 30 frames ≈ a few cents on Sonnet.")

            st.markdown("### Step 3 — Extract Frames")
            if st.button("🎞️ Extract Frames", use_container_width=True, key="va_extract"):
                with st.spinner(f"Extracting at {fps_c} fps…"):
                    try:
                        suffix = ".mp4" if va_vid.name.lower().endswith(".mp4") else ".mov"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(va_vid.read())
                            tmp_path = tmp.name
                        frames = extract_frames(tmp_path, fps=fps_c)
                        os.unlink(tmp_path)
                        if not frames:
                            st.error("No frames extracted — check file format/codec.")
                        else:
                            st.session_state.va_frames = frames
                            st.session_state.va_frame_count = len(frames)
                            st.session_state.va_video_name = va_vid.name
                            st.session_state.va_fps_used = fps_c
                            st.session_state.va_analysis_result = ""
                            st.success(f"✅ {len(frames)} frames extracted from {va_vid.name}")
                    except Exception as e:
                        st.error(f"❌ Extraction failed: {e}")

        # Once frames are loaded, allow analysis
        if st.session_state.va_frame_count > 0:
            frames = st.session_state.va_frames
            n = st.session_state.va_frame_count
            fps_u = st.session_state.va_fps_used
            vname = st.session_state.va_video_name

            st.markdown("---")
            st.markdown(f"**{n} frames loaded** from `{vname}` — ~{n / fps_u:.0f}s of footage.")

            # Frame range selector
            st.markdown("### Step 4 — Select Frame Range")
            if n == 1:
                sf, ef = 1, 1
            else:
                sf, ef = st.slider("varange", 1, n, (1, min(n, 30)), key="va_range")
            sel = ef - sf + 1
            st.caption(f"Frames {sf}–{ef} | {sel} frames | "
                       f"{(sf - 1) / fps_u:.1f}s–{ef / fps_u:.1f}s")

            # Frame preview
            with st.expander(f"🔍 Preview {sel} selected frames", expanded=(sel <= 15)):
                prev = frames[sf - 1: ef][:25]
                cols = st.columns(5)
                for i, fb in enumerate(prev):
                    with cols[i % 5]:
                        st.image(
                            base64.b64decode(fb),
                            caption=f"F{sf + i} ~{(sf + i - 1) / fps_u:.1f}s",
                            use_container_width=True,
                        )

            # Question / context input
            st.markdown("### Step 5 — Your Question / Context")
            va_q = st.text_area(
                "vaq_label",
                height=110,
                placeholder=("e.g. 'Was the serve legal? Check upward arc, paddle "
                             "head vs wrist, ball-at-waist.'  OR  'Did the player "
                             "commit an NVZ momentum fault on the volley?'  OR  "
                             "'Was the line call correct on this rally-ending shot?'"),
                label_visibility="collapsed",
                key="va_q",
            )

            can_run = bool(va_q.strip()) and api_key_ok()
            if not api_key_ok():
                st.warning("⚠️ Enter your Anthropic API key in the sidebar.")
            if st.button(f"🎬 Analyze {sel} Frames",
                         disabled=not can_run, use_container_width=True, key="va_run"):
                content_blocks = build_vision_content(
                    frames, sf - 1, ef - 1, va_q, vname, fps_u,
                    preamble_extra=(
                        "Begin with a Visibility Check. Cite EXACT 2026 USAPA "
                        "rule numbers (e.g. Rule 11.A.2). Use 'Frame N' format."
                    ),
                )
                st.markdown("---")
                st.markdown("#### 🎬 Pickle Rick Video Analysis")
                client = make_client()
                ph = st.empty()
                full = ""
                try:
                    with st.spinner(f"Analyzing {sel} frames… (15–60 seconds)"):
                        for chunk in stream_vision(client, content_blocks, VIDEO_SYSTEM_PROMPT):
                            full += chunk
                            ph.markdown(full + "▌")
                    ph.markdown(full)
                    st.session_state.va_analysis_result = full
                except Exception as e:
                    st.error(handle_api_error(e))

            # Download analysis if available
            if st.session_state.va_analysis_result:
                st.markdown("---")
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "⬇️ Download Analysis (.txt)",
                    data=st.session_state.va_analysis_result,
                    file_name=f"picklerick_analysis_{ts}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

        elif not va_vid:
            st.markdown("---")
            st.markdown(f"""<div class="pr-card-green">
            <h4 style="margin-top:0;color:{GREEN_DARK};">How the Video Analyzer Works</h4>
            <ol style="color:{TEXT};line-height:2.0;">
            <li>Upload a .mp4 or .mov clip (10–60 seconds is ideal)</li>
            <li>Set extraction fps — 0.5 overview, 1.0 standard, 2.0 fast action</li>
            <li>Extract Frames — OpenCV processes the clip server-side</li>
            <li>Select frame range — focus on the key play</li>
            <li>Ask your question — serve legality? NVZ fault? line call?</li>
            <li>Get frame-by-frame analysis citing exact 2026 USAPA rules</li>
            </ol></div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — QUIZ
# ─────────────────────────────────────────────────────────────────────────────

with tab_quiz:
    st.markdown("## 📝 Pickle Rick Quiz")
    st.markdown("Sharpen your 2026 USAPA rules knowledge. Single-question or 10-question modes.")

    # Topic + mode selectors
    qc1, qc2 = st.columns([3, 2])
    with qc1:
        topic = st.selectbox(
            "Topic",
            options=["Mixed", "2026 Changes", "Serving", "NVZ",
                     "Line Calls", "Scoring", "Faults", "Tournament",
                     "Wheelchair / Adaptive", "Conduct"],
            index=0, key="quiz_topic_select",
        )
        if topic != st.session_state.quiz_topic:
            st.session_state.quiz_topic = topic
            # Reset 10Q if topic changes
            st.session_state.tenq_questions = []
            st.session_state.tenq_index = 0
            st.session_state.tenq_answers = []
            st.session_state.tenq_finished = False

    with qc2:
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if st.button("🎯 Single Question Mode", use_container_width=True, key="mode_single"):
                st.session_state.quiz_mode = "single"
                st.session_state.quiz_current_q = None
                st.session_state.quiz_answered = False
                st.session_state.quiz_user_answer = None
                st.rerun()
        with mode_col2:
            if st.button("📚 10 Question Quiz", use_container_width=True, key="mode_ten"):
                st.session_state.quiz_mode = "ten"
                st.session_state.tenq_questions = []
                st.session_state.tenq_index = 0
                st.session_state.tenq_answers = []
                st.session_state.tenq_finished = False
                st.session_state.tenq_answered_this = False
                st.session_state.tenq_user_answer = None
                st.rerun()

    st.markdown("---")

    # ── SINGLE-QUESTION MODE ──────────────────────────────────────────────────
    if st.session_state.quiz_mode == "single":
        # Generate a new question if needed
        if st.session_state.quiz_current_q is None:
            with st.spinner("Generating question…"):
                q = generate_single_question(
                    st.session_state.quiz_topic, st.session_state.quiz_session_topics,
                )
            if q:
                st.session_state.quiz_current_q = q
                st.session_state.quiz_answered = False
                st.session_state.quiz_user_answer = None
                st.session_state.quiz_session_topics.append(q.get("topic", "?"))

        q = st.session_state.quiz_current_q
        if q:
            if st.session_state.quiz_total > 0:
                accuracy_display(st.session_state.quiz_correct, st.session_state.quiz_total)
            render_question_card(q)
            options = q.get("options", {})
            if not st.session_state.quiz_answered:
                option_labels = [f"{k}:  {v}" for k, v in sorted(options.items())]
                user_choice = st.radio(
                    "**Select your answer:**", option_labels,
                    key=f"single_radio_{st.session_state.quiz_total}",
                )
                if st.button("✅ Submit", use_container_width=True, key="single_submit"):
                    chosen = user_choice.split(":")[0].strip()
                    st.session_state.quiz_user_answer = chosen
                    st.session_state.quiz_answered = True
                    st.session_state.quiz_total += 1
                    if chosen == q.get("correct", ""):
                        st.session_state.quiz_correct += 1
                    st.rerun()
            else:
                render_feedback(q, st.session_state.quiz_user_answer)
                st.markdown("")
                if st.button("➡️ Next Question", use_container_width=True, key="single_next"):
                    st.session_state.quiz_current_q = None
                    st.session_state.quiz_answered = False
                    st.session_state.quiz_user_answer = None
                    st.rerun()

    # ── 10-QUESTION QUIZ MODE ─────────────────────────────────────────────────
    elif st.session_state.quiz_mode == "ten":
        # Generate batch
        if not st.session_state.tenq_questions:
            with st.spinner("Generating 10-question quiz… (~30 seconds)"):
                qs = generate_ten_questions(st.session_state.quiz_topic)
            if qs:
                st.session_state.tenq_questions = qs
                st.session_state.tenq_index = 0
                st.session_state.tenq_answers = []
                st.session_state.tenq_finished = False

        if (st.session_state.tenq_questions and not st.session_state.tenq_finished):
            idx = st.session_state.tenq_index
            total_qs = len(st.session_state.tenq_questions)
            if idx < total_qs:
                q = st.session_state.tenq_questions[idx]
                st.markdown(f"**Question {idx + 1} of {total_qs}** — Topic: *{st.session_state.quiz_topic}*")
                options = q.get("options", {})
                render_question_card(q, question_num=f"Q{idx + 1}.")

                if not st.session_state.tenq_answered_this:
                    option_labels = [f"{k}:  {v}" for k, v in sorted(options.items())]
                    user_choice = st.radio(
                        "**Select your answer:**", option_labels,
                        key=f"tenq_radio_{idx}",
                    )
                    if st.button("✅ Submit Answer", use_container_width=True, key=f"tenq_submit_{idx}"):
                        chosen = user_choice.split(":")[0].strip()
                        st.session_state.tenq_user_answer = chosen
                        st.session_state.tenq_answered_this = True
                        is_correct = chosen == q.get("correct", "")
                        st.session_state.tenq_answers.append({
                            "question_num": idx + 1,
                            "user": chosen, "correct": q.get("correct", ""),
                            "is_correct": is_correct, "data": q,
                        })
                        st.rerun()
                else:
                    render_feedback(q, st.session_state.tenq_user_answer)
                    st.markdown("")
                    is_last = (idx == total_qs - 1)
                    btn_lbl = "📊 See Final Score" if is_last else f"➡️ Next ({idx + 2}/{total_qs})"
                    if st.button(btn_lbl, use_container_width=True, key=f"tenq_next_{idx}"):
                        if is_last:
                            st.session_state.tenq_finished = True
                        else:
                            st.session_state.tenq_index += 1
                            st.session_state.tenq_answered_this = False
                            st.session_state.tenq_user_answer = None
                        st.rerun()

        elif st.session_state.tenq_finished and st.session_state.tenq_answers:
            answers = st.session_state.tenq_answers
            n_correct = sum(1 for a in answers if a["is_correct"])
            n_total = len(answers)
            pct = int(round(n_correct / n_total * 100))
            score_color = (GREEN_DARK if pct >= 80 else (AMBER if pct >= 60 else RED))
            grade_label = ("🏆 Excellent!" if pct >= 90 else "✅ Good" if pct >= 80
                           else "📈 Getting there" if pct >= 70 else "📚 Keep studying"
                           if pct >= 60 else "🔁 Review the rulebook")

            st.markdown(f"""
            <div style="background:{CARD};border:2px solid {score_color};border-radius:14px;
                        padding:2rem;text-align:center;margin-bottom:1.5rem;
                        box-shadow:0 4px 16px rgba(34,197,94,0.10);">
                <div style="font-size:3.5rem;font-weight:900;color:{score_color};">{pct}%</div>
                <div style="font-size:1.3rem;font-weight:700;color:{TEXT};margin:0.3rem 0;">
                    {n_correct} / {n_total} correct &nbsp; {grade_label}</div>
                <div style="color:{MUTED};font-size:0.9rem;">Topic: {st.session_state.quiz_topic}</div>
            </div>""", unsafe_allow_html=True)

            ra1, ra2 = st.columns(2)
            with ra1:
                if st.button("📁 Save Results to Pickle Log", use_container_width=True, key="tenq_save"):
                    st.session_state.quiz_log.append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "topic": st.session_state.quiz_topic,
                        "score": pct, "correct": n_correct, "total": n_total,
                        "answers": answers,
                    })
                    st.success(f"✅ Saved! {len(st.session_state.quiz_log)} quiz log(s) on file.")
            with ra2:
                if st.button("🔄 Take Another Quiz", use_container_width=True, key="tenq_restart"):
                    st.session_state.tenq_questions = []
                    st.session_state.tenq_index = 0
                    st.session_state.tenq_answers = []
                    st.session_state.tenq_finished = False
                    st.session_state.tenq_answered_this = False
                    st.session_state.tenq_user_answer = None
                    st.rerun()

            st.markdown("---")
            st.markdown("### 📋 Full Review")
            for a in answers:
                qd = a["data"]
                opts = qd.get("options", {})
                u, c, ic = a["user"], a["correct"], a["is_correct"]
                icon = "✅" if ic else "❌"
                cbg = "#F0FDF4" if ic else "#FFF1F2"
                cbo = GREEN if ic else "#F87171"
                u_txt, c_txt = opts.get(u, u), opts.get(c, c)
                corr_line = (
                    "" if ic
                    else f'<br><strong style="color:#7F1D1D;">✔ Correct: {c}: {c_txt}</strong>'
                )
                st.markdown(f"""
                <div style="background:{cbg};border:1.5px solid {cbo};border-radius:10px;
                            padding:1.1rem 1.3rem;margin-bottom:0.9rem;">
                    <div style="font-weight:700;color:{TEXT};">
                        {icon} Q{a["question_num"]}: {qd.get("question","")}</div>
                    <div style="font-size:0.9rem;color:{TEXT};margin-top:0.3rem;">
                        <strong>Your answer:</strong> {u}: {u_txt}{corr_line}</div>
                </div>""", unsafe_allow_html=True)
                with st.expander(f"📖 Explanation — Q{a['question_num']}", expanded=False):
                    p = qd.get("personal_note", "")
                    pnote = f'<br><strong>📋 From your notes:</strong> {p}' if p else ""
                    st.markdown(f"""<div class="quiz-explanation">
                    {qd.get("explanation","")}<br><br>
                    <strong>📌 Citation:</strong> {qd.get("rule_citation","")}{pnote}
                    </div>""", unsafe_allow_html=True)

            if st.session_state.quiz_log:
                st.markdown("---")
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    f"⬇️ Download All Quiz Results ({len(st.session_state.quiz_log)} saved)",
                    data=json.dumps(st.session_state.quiz_log, indent=2, ensure_ascii=False),
                    file_name=f"picklerick_quiz_{ts}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    elif st.session_state.quiz_mode is None:
        st.markdown(f"""<div class="pr-card" style="text-align:center;padding:1.5rem;">
        <p style="color:{MUTED};margin:0;">👆 Pick Single Question Mode or 10-Question mode above.</p>
        </div>""", unsafe_allow_html=True)


# =============================================================================
# FOOTER
# =============================================================================

st.markdown(f"""
<div class="pr-footer">
    <strong style="color:{GREEN_DARK};">Pickleball rules AI assistant trained on USAPA rulebook
    and all recent updates.</strong><br>
    Built for picklers, by a pickler 🥒 &nbsp;|&nbsp;
    Pickle Rick v1.0 &nbsp;|&nbsp;
    2026 USAPA Official Rulebook + 2026 Change Document<br>
    <span style="font-size:0.72rem;">
    Not official USAPA interpretation — confirm with a certified referee or tournament director if needed.
    </span>
</div>
""", unsafe_allow_html=True)
