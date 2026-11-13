"""Eligibility orchestration. Decisions are made only from verified rules."""
from backend.eligibility.evaluator import evaluate_condition


class EligibilityEngine:
    def __init__(self, repository):
        self.repository = repository

    def check_scheme(self, scheme_id: str, profile: dict) -> dict:
        scheme = self.repository.get_scheme(scheme_id, verified_only=True)
        if not scheme:
            raise LookupError("Verified scheme not found. Unverified schemes cannot produce eligibility decisions.")

        rules = self.repository.get_rules(scheme_id)
        if not rules:
            return self._result(scheme, "NEEDS_MORE_INFORMATION", [], ["No verified eligibility rules are available for this scheme."], [])

        evaluations = []
        for rule in rules:
            result = evaluate_condition(rule["condition"], profile)
            evaluations.append((rule, result))

        # Every top-level rule is mandatory (AND). Use nested any/all for alternatives.
        mandatory_evaluations = [(rule, result) for rule, result in evaluations if rule.get("is_mandatory", 1)]
        statuses = [result.status for _, result in mandatory_evaluations]
        if not mandatory_evaluations:
            status = "NEEDS_MORE_INFORMATION"
        elif "FALSE" in statuses:
            status = "NOT_ELIGIBLE"
        elif "UNKNOWN" in statuses:
            status = "NEEDS_MORE_INFORMATION"
        else:
            status = "ELIGIBLE"

        missing, reasons, sources = [], [], []
        for rule, result in evaluations:
            reasons.extend([f"{rule['rule_name']}: {r}" for r in result.reasons])
            if rule.get("is_mandatory", 1):
                missing.extend(result.missing_attributes)
            sources.extend(rule.get("sources", []))

        return self._result(scheme, status, list(dict.fromkeys(missing)), list(dict.fromkeys(reasons)), _unique_sources(sources))

    def match_schemes(self, profile: dict) -> list[dict]:
        results = []
        for scheme in self.repository.list_schemes(verified_only=True):
            try:
                results.append(self.check_scheme(scheme["scheme_id"], profile))
            except (ValueError, LookupError):
                continue
        order = {"ELIGIBLE": 0, "NEEDS_MORE_INFORMATION": 1, "NOT_ELIGIBLE": 2}
        return sorted(results, key=lambda item: order[item["status"]])

    @staticmethod
    def _result(scheme, status, missing, reasons, sources):
        return {
            "scheme_id": scheme["scheme_id"],
            "scheme_name": scheme["scheme_name"],
            "status": status,
            "missing_attributes": missing,
            "reasons": reasons,
            "sources": sources,
            "disclaimer": "Preliminary rule-based assessment, not an official approval or guarantee of benefit. Verify current criteria with the issuing department."
        }


def _unique_sources(sources):
    seen, output = set(), []
    for source in sources:
        key = (source.get("document_name"), source.get("page_number"), source.get("url"))
        if key not in seen:
            seen.add(key)
            output.append(source)
    return output
