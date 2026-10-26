"""
Strict SQL Read-Only Security Validator and AST Auditor.
Prevents SQL injection, stacked queries, data modification, and unauthorized table access.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Token, Statement
from sqlparse.tokens import DML, Keyword, Punctuation

# Allowed tables in our database schema
ALLOWED_TABLES: Set[str] = {
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "marketing_spend"
}

# Forbidden keywords indicating writes, DDL, administrative commands, or dangerous extensions
FORBIDDEN_KEYWORDS: Set[str] = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE",
    "REPLACE", "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "EXEC",
    "EXECUTE", "UPSERT", "MERGE", "CALL", "LOAD_EXTENSION", "WRITELOG",
    "INTO", "OUTFILE", "DUMPFILE"
}

# Dangerous patterns including sqlite comments, stacked statements, or shell escapes
DISALLOWED_PATTERNS = [
    re.compile(r";\s*\S+", re.IGNORECASE),          # Multiple statements separated by semicolon
    re.compile(r"--", re.IGNORECASE),               # SQL inline comment trickery
    re.compile(r"/\*.*?\*/", re.DOTALL),            # Block comments
    re.compile(r"xp_\w+", re.IGNORECASE),           # Windows shell procedures
    re.compile(r"sqlite_master\s+set", re.IGNORECASE)
]


class SQLValidationError(Exception):
    """Raised when a SQL query violates security or read-only constraints."""
    pass


class SQLSecurityValidator:
    """
    Validates that incoming queries are strictly read-only SELECT statements
    operating exclusively on allowed schema tables.
    """

    def __init__(self, allowed_tables: Optional[Set[str]] = None):
        self.allowed_tables = {t.lower() for t in (allowed_tables or ALLOWED_TABLES)}

    def sanitize(self, raw_query: str) -> str:
        """Strip markdown ticks, whitespace, and clean trailing semicolons."""
        if not raw_query:
            return ""
        q = raw_query.strip()
        # Remove markdown code fence ```sql ... ```
        q = re.sub(r"^```(?:sql)?\s*", "", q, flags=re.IGNORECASE)
        q = re.sub(r"\s*```$", "", q)
        q = q.strip()
        # Remove single trailing semicolon if present
        if q.endswith(";"):
            q = q[:-1].strip()
        return q

    def validate(self, raw_query: str) -> Dict[str, any]:
        """
        Validates the SQL query. Returns a dict:
        {
            "is_valid": bool,
            "sanitized_query": str,
            "tables_accessed": list[str],
            "error": Optional[str]
        }
        """
        query = self.sanitize(raw_query)

        if not query:
            return {
                "is_valid": False,
                "sanitized_query": "",
                "tables_accessed": [],
                "error": "Query is empty."
            }

        # Check for multiple stacked statements (e.g. semicolon followed by another statement)
        if ";" in query:
            statements = [s.strip() for s in query.split(";") if s.strip()]
            if len(statements) > 1:
                return {
                    "is_valid": False,
                    "sanitized_query": query,
                    "tables_accessed": [],
                    "error": "Multiple stacked SQL statements are forbidden. Only single read-only queries are permitted."
                }
            query = statements[0]

        # Parse AST with sqlparse
        parsed = sqlparse.parse(query)
        if not parsed:
            return {
                "is_valid": False,
                "sanitized_query": query,
                "tables_accessed": [],
                "error": "Failed to parse SQL statement."
            }

        if len(parsed) > 1:
            return {
                "is_valid": False,
                "sanitized_query": query,
                "tables_accessed": [],
                "error": "Multiple SQL statements detected."
            }

        stmt = parsed[0]

        # Check statement type: Must be SELECT or WITH (for CTEs)
        stmt_type = stmt.get_type().upper()
        if stmt_type not in ("SELECT", "WITH", "UNKNOWN"):
            return {
                "is_valid": False,
                "sanitized_query": query,
                "tables_accessed": [],
                "error": f"Disallowed statement type: '{stmt_type}'. Only read-only SELECT/CTE queries are allowed."
            }

        # Check for forbidden keywords across all tokens
        for token in stmt.flatten():
            token_str = token.value.strip().upper()
            if token_str in FORBIDDEN_KEYWORDS:
                return {
                    "is_valid": False,
                    "sanitized_query": query,
                    "tables_accessed": [],
                    "error": f"Forbidden keyword detected: '{token_str}'. Only read-only operations are permitted."
                }

        # Extract and validate table references
        tables_found = self._extract_tables(stmt)
        for tbl in tables_found:
            tbl_clean = tbl.lower()
            # Allow common CTE alias names or subquery aliases
            if tbl_clean not in self.allowed_tables:
                # If query contains WITH, this table might be an internal CTE name
                if not (stmt_type == "WITH" or "with " in query.lower()):
                    return {
                        "is_valid": False,
                        "sanitized_query": query,
                        "tables_accessed": tables_found,
                        "error": f"Unauthorized table access: '{tbl}'. Query is restricted to approved sales schema tables."
                    }

        return {
            "is_valid": True,
            "sanitized_query": query,
            "tables_accessed": tables_found,
            "error": None
        }

    def _extract_tables(self, statement: Statement) -> List[str]:
        """Extract table names from FROM and JOIN clauses."""
        tables = []
        from_seen = False
        clause_break_keywords = {
            "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT",
            "UNION", "EXCEPT", "INTERSECT", "WINDOW", "OFFSET"
        }

        for token in statement.tokens:
            val_upper = token.value.strip().upper()

            if from_seen:
                if any(val_upper.startswith(kw) for kw in clause_break_keywords):
                    from_seen = False
                elif val_upper in ("JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"):
                    continue
                elif val_upper == "ON":
                    # The ON condition is not a table name, wait for next JOIN or clause break
                    from_seen = False
                elif self._is_subselect(token):
                    tables.extend(self._extract_tables(token))
                else:
                    extracted = self._extract_table_names(token)
                    tables.extend(extracted)
            elif val_upper in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"):
                from_seen = True

        # Filter out empty or whitespace strings
        cleaned = [t.strip('`"\'[]') for t in tables if t and t.strip()]
        return list(dict.fromkeys(cleaned))

    def _is_subselect(self, token: Token) -> bool:
        if not token.is_group:
            return False
        for subtoken in token.tokens:
            if subtoken.ttype is DML and subtoken.value.upper() == "SELECT":
                return True
        return False

    def _extract_table_names(self, token: Token) -> List[str]:
        tables = []
        if isinstance(token, IdentifierList):
            for identifier in token.get_identifiers():
                tbl = identifier.get_real_name()
                if tbl:
                    tables.append(tbl)
        elif isinstance(token, Identifier):
            tbl = token.get_real_name()
            if tbl:
                tables.append(tbl)
        elif token.ttype is None and hasattr(token, 'tokens'):
            for sub in token.tokens:
                if isinstance(sub, Identifier):
                    tbl = sub.get_real_name()
                    if tbl:
                        tables.append(tbl)
        return tables


# Convenience singleton
validator = SQLSecurityValidator()

def validate_sql(query: str) -> Dict[str, any]:
    return validator.validate(query)
