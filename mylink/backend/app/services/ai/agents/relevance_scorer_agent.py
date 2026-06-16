from typing import Any, Dict, List, Optional, Tuple
import math

from app.services.ai import Agent


EDU_ORDER = [
    "highschool",
    "certificate",
    "associate",
    "bachelor",
    "master",
    "phd",
]

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _rank(value: Optional[str], order: List[str], normalize_lower: bool = True) -> Optional[int]:
    if not value:
        return None
    v = value.strip()
    v = v.lower() if normalize_lower else v
    try:
        return order.index(v)
    except ValueError:
        return None


def _best_lang_level(items: List[Dict[str, Any]]) -> Optional[str]:
    best_idx = None
    best_level = None
    for it in items or []:
        lvl = (it.get("level") or "").upper()
        if lvl in CEFR_ORDER:
            idx = CEFR_ORDER.index(lvl)
            if best_idx is None or idx > best_idx:
                best_idx = idx
                best_level = lvl
    return best_level


def _collect_evidence(mismatches: List[Dict[str, Any]], max_items: int = 2) -> Dict[str, List[str]]:
    def trim_words(s: str, limit: int = 12) -> str:
        words = (s or "").split()
        return " ".join(words[:limit])

    jd_quotes: List[str] = []
    cv_quotes: List[str] = []
    for m in mismatches or []:
        ev = m.get("evidence") or {}
        if isinstance(ev, dict):
            if ev.get("jd") and len(jd_quotes) < max_items:
                jd_quotes.append(trim_words(str(ev.get("jd"))))
            if ev.get("cv") and len(cv_quotes) < max_items:
                cv_quotes.append(trim_words(str(ev.get("cv"))))
        if len(jd_quotes) >= max_items and len(cv_quotes) >= max_items:
            break
    return {"jd": jd_quotes, "cv": cv_quotes}


def _skills_set(skills: Optional[List[str]]) -> set:
    return {str(s).strip().lower() for s in (skills or []) if str(s).strip()}


def _has_all(required: set, actual: set) -> bool:
    return required.issubset(actual)


def _parse_number_from_text(text: str) -> Optional[int]:
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None


class RelevanceScorerAgent(Agent):
    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ids = payload.get("ids") or {}
        job = payload.get("job_struct") or {}
        cv = payload.get("cv_struct") or {}
        mismatches = payload.get("mismatches") or []
        missing_data = payload.get("missing_data") or []
        widget = payload.get("widget_payload") or {}
        findings = (widget.get("dialogFindings") or {}) if isinstance(widget, dict) else {}
        weights_mode = (payload.get("weights_mode") or "auto").lower()
        weights_given = payload.get("weights") or {}
        must_have_skills = payload.get("must_have_skills") or []
        thresholds = payload.get("verdict_thresholds") or {"fit": 75, "borderline": 60}

        # Collect evidence
        evidence = _collect_evidence(mismatches)

        # Experience pct
        job_min_exp = int(job.get("min_experience_years") or 0)
        cv_total_exp = int(cv.get("total_experience_years") or 0)
        clarified_exp = _extract_clarified_experience(findings)
        exp_years = clarified_exp if clarified_exp is not None else cv_total_exp
        experience_pct, exp_note = self._calc_experience_pct(exp_years, job_min_exp)

        # Skills pct
        req_skills = _skills_set(job.get("required_skills"))
        cv_skills = _skills_set(cv.get("skills"))
        skills_pct, skills_note = self._calc_skills_pct(req_skills, cv_skills, must_have_skills, findings)

        # Education pct
        edu_min = (job.get("education_min") or "unknown").lower()
        edu_level = (cv.get("education_level") or "unknown").lower()
        education_pct, edu_note = self._calc_education_pct(edu_min, edu_level)

        # Langs pct
        jd_langs = job.get("lang_requirement") or []
        cv_langs = cv.get("langs") or []
        langs_pct, langs_note = self._calc_langs_pct(jd_langs, cv_langs)

        # Location pct
        location_pct, loc_note = self._calc_location_pct(job, cv, findings)

        # Domain pct
        domain_pct, domain_note = self._calc_domain_pct(job, cv)

        # Compensation pct
        comp_pct, comp_note = self._calc_comp_pct(job, cv, findings)

        scores_pct = {
            "experience": experience_pct,
            "skills": skills_pct,
            "education": education_pct,
            "langs": langs_pct,
            "location": location_pct,
            "domain": domain_pct,
            "comp": comp_pct,
        }

        # Weights
        weights = self._calc_weights(weights_mode, weights_given, job, must_have_skills)

        # Overall
        overall = int(round(sum(weights[k] * scores_pct[k] for k in scores_pct)))
        overall = max(0, min(100, overall))

        # Verdict
        must_have_covered = _has_all(_skills_set(must_have_skills), cv_skills)
        serious_risk = self._has_serious_risk(mismatches)
        fit_thr = int(thresholds.get("fit") or 75)
        borderline_thr = int(thresholds.get("borderline") or 60)
        if overall >= fit_thr and must_have_covered:
            verdict = "подходит"
        elif overall >= borderline_thr or serious_risk:
            verdict = "сомнительно"
        else:
            verdict = "не подходит"

        # Summary
        summary = self._build_summary(job, cv, scores_pct, mismatches, missing_data, findings)

        # Calc notes
        calc_notes = [n for n in [
            exp_note,
            skills_note,
            edu_note,
            langs_note,
            loc_note,
            domain_note,
            comp_note,
            self._weights_note(weights_mode),
        ] if n]

        # Dialog findings passthrough
        dialog_used = {
            "relocation_ready": bool(findings.get("relocation_ready") or False),
            "salary_flex": findings.get("salary_flex") or "",
            "lang_proofs": findings.get("lang_proofs") or [],
            "other_clarifications": findings.get("other_clarifications") or [],
        }

        return {
            "ids": {
                "job_id": ids.get("job_id") or "",
                "candidate_id": ids.get("candidate_id") or "",
                "application_id": ids.get("application_id") or "",
            },
            "weights": weights,
            "scores_pct": scores_pct,
            "overall_match_pct": overall,
            "verdict": verdict,
            "summary": summary,
            "evidence": evidence,
            "dialog_findings_used": dialog_used,
            "calc_notes": calc_notes,
            "version": "v1.0",
        }

    # -------- Calculations --------
    def _calc_experience_pct(self, cv_years: int, job_min: int) -> Tuple[int, str]:
        if job_min <= 0:
            return 100, "JD не задаёт минимум по опыту"
        if cv_years >= job_min:
            return 100, "Опыт не ниже минимального"
        if job_min > 0:
            raw = int(round(100 * (cv_years / job_min)))
            if cv_years < 0.7 * job_min:
                return min(raw, 60), "Опыт ниже 70% минимума — применён потолок 60"
            return max(0, min(100, raw)), "Опыт ниже минимума"
        return 70, "Нет данных о минимуме — использовано значение по умолчанию"

    def _calc_skills_pct(self, req: set, cv: set, must_have_skills: List[str], findings: Dict[str, Any]) -> Tuple[int, str]:
        if not req:
            return 100, "JD не задаёт список обязательных навыков"
        overlap = len(req.intersection(cv))
        base = int(round(100 * (overlap / max(1, len(req)))))

        # Cap if any must-have missing
        must_have = _skills_set(must_have_skills)
        if not _has_all(must_have, cv):
            base = min(base, 60)
            note = "Отсутствует один или более must-have — применён потолок 60"
        else:
            note = "Навыки покрыты пропорционально обязательным требованиям"

        # Consider explicit equivalences only if declared in findings.other_clarifications
        # e.g., "skills:fastapi=продакшн 8 мес" — keep conservative; do not mutate base here beyond must-have cap
        return base, note

    def _calc_education_pct(self, edu_min: str, edu_level: str) -> Tuple[int, str]:
        if edu_min == "unknown":
            return 100, "JD не задаёт минимальный уровень образования"
        r_min = _rank(edu_min, EDU_ORDER)
        r_lv = _rank(edu_level, EDU_ORDER)
        if r_lv is None:
            return 50, "Нет данных об образовании кандидата"
        if r_lv >= r_min:
            return 100, "Уровень образования соответствует или выше минимального"
        diff = r_min - r_lv
        if diff == 1:
            return 70, "Образование на один уровень ниже минимального"
        return 40, "Образование на два и более уровней ниже минимального"

    def _calc_langs_pct(self, jd_langs: List[Dict[str, Any]], cv_langs: List[Dict[str, Any]]) -> Tuple[int, str]:
        req = _best_lang_level(jd_langs)
        got = _best_lang_level(cv_langs)
        if not req:
            return 100, "JD не задаёт языковой минимум"
        if not got:
            return 60, "Нет данных об уровне языка кандидата"
        d = CEFR_ORDER.index(got) - CEFR_ORDER.index(req)
        if d >= 0:
            return 100, "Уровень языка соответствует или выше минимума"
        if d == -1:
            return 75, "Уровень языка ниже на один уровень"
        return 50, "Уровень языка ниже на два и более уровней"

    def _calc_location_pct(self, job: Dict[str, Any], cv: Dict[str, Any], findings: Dict[str, Any]) -> Tuple[int, str]:
        jr = job.get("location_requirement") or {}
        job_city = (jr.get("city") or "").strip().lower()
        job_fmt = (jr.get("employment_type") or "unknown").strip().lower()
        cv_city = ((cv.get("location") or {}).get("city") or "").strip().lower()
        cv_fmt = (cv.get("employment_type") or "unknown").strip().lower()

        if not job_city and (job_fmt == "unknown" or not job_fmt):
            return 100, "JD не фиксирует локацию или формат"

        if job_city and cv_city == job_city and job_fmt and cv_fmt == job_fmt:
            return 100, "Локация и формат совпадают"

        if findings.get("relocation_ready"):
            return 80, "Готовность к переезду"

        if job_fmt in {"office", "hybrid"} and cv_fmt == "remote":
            return 40, "Удалёнка при офисном/гибридном формате JD"

        return 60, "Частичное соответствие локации/формата или недостаточно данных"

    def _calc_domain_pct(self, job: Dict[str, Any], cv: Dict[str, Any]) -> Tuple[int, str]:
        jd_dom = (job.get("domain") or "").strip().lower()
        cv_tags = [str(t).strip().lower() for t in (cv.get("domain_tags") or [])]
        if not jd_dom:
            return 100, "JD не задаёт домен"
        if jd_dom in cv_tags:
            return 100, "Есть явный опыт в домене JD"
        for t in cv_tags:
            if jd_dom in t or t in jd_dom:
                return 80, "Найден смежный доменный опыт"
        return 60, "Нет указаний на доменный опыт"

    def _calc_comp_pct(self, job: Dict[str, Any], cv: Dict[str, Any], findings: Dict[str, Any]) -> Tuple[int, str]:
        jr = job.get("salary_range") or {}
        if not jr:
            return 100, "JD не задаёт вилку компенсации"
        jmin = float(jr.get("min") or 0)
        jmax = float(jr.get("max") or 0)
        exp_block = cv.get("salary_expectation") or {}
        if not exp_block:
            return 70, "Нет данных об ожиданиях кандидата"
        if exp_block.get("unknown"):
            return 70, "Ожидания кандидата не указаны"
        value = float(exp_block.get("value") or 0)
        if jmin <= value <= jmax:
            base = 100
            note = "Ожидания внутри вилки JD"
        else:
            if value <= 0 or jmax <= 0:
                return 70, "Недостаточно данных по вилке/ожиданиям"
            if value > jmax:
                pct_over = (value - jmax) / jmax
            else:
                pct_over = (jmin - value) / max(jmax, 1.0)
            if 0 < pct_over <= 0.10:
                base = 80
                note = "Ожидания отличаются ≤10%"
            elif pct_over <= 0.25:
                base = 60
                note = "Ожидания отличаются >10–25%"
            else:
                base = 30
                note = "Ожидания отличаются >25%"
        if (findings.get("salary_flex") or "").lower() == "negotiable":
            boosted = min(100, base + 10)
            return boosted, note + "; применён бонус за гибкость +10 п.п."
        return base, note

    def _calc_weights(self, mode: str, given: Dict[str, Any], job: Dict[str, Any], must_have_skills: List[str]) -> Dict[str, float]:
        if mode == "given":
            w = {
                "experience": float(given.get("experience") or 0.30),
                "skills": float(given.get("skills") or 0.35),
                "education": float(given.get("education") or 0.05),
                "langs": float(given.get("langs") or 0.10),
                "location": float(given.get("location") or 0.10),
                "domain": float(given.get("domain") or 0.05),
                "comp": float(given.get("comp") or 0.05),
            }
            return self._normalize_weights(w)

        # auto
        w = {
            "experience": 0.30,
            "skills": 0.35,
            "education": 0.05,
            "langs": 0.10,
            "location": 0.10,
            "domain": 0.05,
            "comp": 0.05,
        }
        if must_have_skills:
            w["skills"] = 0.40
            w["domain"] = 0.03
            w["comp"] = 0.02
        jr = job.get("location_requirement") or {}
        job_fmt = (jr.get("employment_type") or "unknown").strip().lower()
        if job_fmt in {"office", "hybrid"}:
            w["location"] = 0.15
            w["education"] = 0.03
            w["domain"] = 0.04
        return self._normalize_weights(w)

    def _normalize_weights(self, w: Dict[str, float]) -> Dict[str, float]:
        s = sum(w.values())
        if s <= 0:
            # Fallback to default distribution
            w = {
                "experience": 0.30,
                "skills": 0.35,
                "education": 0.05,
                "langs": 0.10,
                "location": 0.10,
                "domain": 0.05,
                "comp": 0.05,
            }
            s = 1.0
        for k in w:
            w[k] = round(w[k] / s, 6)
        return w

    def _weights_note(self, mode: str) -> str:
        return "Режим весов: given" if mode == "given" else "Режим весов: auto с нормализацией до суммы 1.0"

    def _has_serious_risk(self, mismatches: List[Dict[str, Any]]) -> bool:
        critical_criteria = {"skills", "experience", "format", "langs"}
        for m in mismatches or []:
            if (m.get("severity") or "").lower() == "high" and (m.get("criterion") or "").lower() in critical_criteria:
                return True
        return False

    def _build_summary(
        self,
        job: Dict[str, Any],
        cv: Dict[str, Any],
        scores: Dict[str, int],
        mismatches: List[Dict[str, Any]],
        missing_data: List[str],
        findings: Dict[str, Any],
    ) -> Dict[str, Any]:
        one_liner = self._one_liner(scores)
        positives: List[str] = []
        risks: List[str] = []
        unknowns: List[str] = []

        if scores.get("skills", 0) >= 80:
            positives.append("сильное покрытие must-have навыков")
        if scores.get("experience", 0) >= 80:
            positives.append("достаточный релевантный опыт")
        if findings.get("relocation_ready"):
            positives.append("готовность к переезду")
        if (findings.get("salary_flex") or "").lower() == "negotiable":
            positives.append("гибкие ожидания по компенсации")

        for m in mismatches[:3]:
            sev = (m.get("severity") or "").lower()
            crit = (m.get("criterion") or "").lower()
            if sev == "high":
                risks.append(f"высокий риск: {crit}")
            elif sev == "medium":
                risks.append(f"риск: {crit}")

        for md in missing_data[:3]:
            unknowns.append(str(md))

        # Add lang proofs note if present
        if findings.get("lang_proofs"):
            positives.append("есть подтверждения языка")

        return {
            "one_liner": one_liner,
            "positives": positives[:5] or [],
            "risks": risks[:5] or [],
            "unknowns": unknowns[:5] or [],
        }

    def _one_liner(self, scores: Dict[str, int]) -> str:
        if scores.get("experience", 0) < 60 or scores.get("skills", 0) < 60:
            return "Риски по ключевым требованиям; требуется дополнительная проверка."
        if min(scores.values()) >= 80:
            return "Кандидат хорошо соответствует требованиям JD."
        return "Частичное соответствие требованиям; есть моменты для уточнения."


def _extract_clarified_experience(findings: Dict[str, Any]) -> Optional[int]:
    # Attempt to parse from other_clarifications entries like "experience:3"
    for s in findings.get("other_clarifications") or []:
        if isinstance(s, str) and s.lower().startswith("experience:"):
            num = _parse_number_from_text(s.split(":", 1)[1])
            if num is not None:
                return num
    return None
