import json
from backend.database.eligibility_db import get_connection


class EligibilityRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def add_scheme(self, scheme: dict):
        with get_connection(self.db_path) as conn:
            conn.execute("""INSERT INTO schemes
                (scheme_id, scheme_name, government_level, department, official_url,
                 verification_status, last_verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scheme_id) DO UPDATE SET
                scheme_name=excluded.scheme_name, government_level=excluded.government_level,
                department=excluded.department, official_url=excluded.official_url,
                verification_status=excluded.verification_status,
                last_verified_at=excluded.last_verified_at, updated_at=CURRENT_TIMESTAMP""",
                (scheme["scheme_id"], scheme["scheme_name"], scheme.get("government_level"),
                 scheme.get("department"), scheme.get("official_url"),
                 scheme.get("verification_status", "unverified"), scheme.get("last_verified_at")))

    def replace_rules(self, scheme_id: str, rules: list[dict]):
        """Replace a scheme's complete rule set, including its source records."""
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM eligibility_rules WHERE scheme_id = ?", (scheme_id,))
            for rule in rules:
                cursor = conn.execute(
                    "INSERT INTO eligibility_rules (scheme_id, rule_name, condition_json, is_mandatory) VALUES (?, ?, ?, ?)",
                    (scheme_id, rule["rule_name"], json.dumps(rule["condition"], ensure_ascii=False), int(rule.get("is_mandatory", True)))
                )
                rule_id = cursor.lastrowid
                for source in rule.get("sources", []):
                    conn.execute("""INSERT INTO rule_sources
                        (rule_id, document_name, page_number, url, excerpt) VALUES (?, ?, ?, ?, ?)""",
                        (rule_id, source["document_name"], source.get("page_number"), source.get("url"), source.get("excerpt")))

    def add_rule(self, scheme_id: str, rule: dict):
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO eligibility_rules (scheme_id, rule_name, condition_json, is_mandatory) VALUES (?, ?, ?, ?)",
                (scheme_id, rule["rule_name"], json.dumps(rule["condition"], ensure_ascii=False), int(rule.get("is_mandatory", True)))
            )
            rule_id = cursor.lastrowid
            for source in rule.get("sources", []):
                conn.execute("""INSERT INTO rule_sources
                    (rule_id, document_name, page_number, url, excerpt) VALUES (?, ?, ?, ?, ?)""",
                    (rule_id, source["document_name"], source.get("page_number"), source.get("url"), source.get("excerpt")))
            return rule_id

    def get_scheme(self, scheme_id: str, verified_only=False):
        query = "SELECT * FROM schemes WHERE scheme_id = ?"
        params = [scheme_id]
        if verified_only:
            query += " AND verification_status = 'verified'"
        with get_connection(self.db_path) as conn:
            row = conn.execute(query, params).fetchone()
            return dict(row) if row else None

    def list_schemes(self, verified_only=True):
        query = "SELECT * FROM schemes"
        if verified_only:
            query += " WHERE verification_status = 'verified'"
        query += " ORDER BY scheme_name"
        with get_connection(self.db_path) as conn:
            return [dict(row) for row in conn.execute(query).fetchall()]

    def get_rules(self, scheme_id: str):
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM eligibility_rules WHERE scheme_id = ? ORDER BY id", (scheme_id,)).fetchall()
            output = []
            for row in rows:
                rule = dict(row)
                rule["condition"] = json.loads(rule.pop("condition_json"))
                sources = conn.execute("SELECT document_name, page_number, url, excerpt FROM rule_sources WHERE rule_id = ?", (rule["id"],)).fetchall()
                rule["sources"] = [dict(source) for source in sources]
                output.append(rule)
            return output
