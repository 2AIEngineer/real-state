import pytest
from django.db import IntegrityError

from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.exceptions import BusinessRuleViolation, InvalidInput
from apps.properties.models import Syndicat
from tests import factories as f

pytestmark = pytest.mark.django_db


class TestApplyChanges:
    def test_only_allowed_fields_present_in_the_changes_are_set(self):
        syndicat = Syndicat(name="Old", city="Lyon")

        fields = apply_changes(
            syndicat,
            {"name": "  New  ", "is_active": False, "unknown": 1},
            allowed=("name", "city"),
        )

        assert fields == ["name"]
        assert syndicat.name == "New"  # text is stripped
        assert syndicat.city == "Lyon"  # not sent: untouched
        assert syndicat.is_active is True  # sent but not allowed: ignored

    def test_nothing_to_apply_returns_no_field(self):
        assert apply_changes(Syndicat(name="A"), {}, allowed=("name",)) == []


class TestTranslateIntegrityErrors:
    def test_a_known_constraint_becomes_a_fresh_domain_error_each_time(self):
        f.make_syndicat(name="Taken")

        def name_taken():
            return InvalidInput("Taken.", field="name", code="name_taken")

        errors = []
        for _ in range(2):
            with pytest.raises(InvalidInput) as exc:
                with translate_integrity_errors({"syndicat_name_ci_unique": name_taken}):
                    Syndicat.objects.create(name="taken")
            errors.append(exc.value)

        assert errors[0] is not errors[1]
        assert errors[0].code == "name_taken"

    def test_a_message_becomes_a_rule_violation_named_after_the_constraint(self):
        f.make_syndicat(name="Taken")

        with pytest.raises(BusinessRuleViolation) as exc:
            with translate_integrity_errors({"syndicat_name_ci_unique": "Already there."}):
                Syndicat.objects.create(name="TAKEN")

        assert exc.value.code == "syndicat_name_ci_unique"

    def test_an_unknown_constraint_is_left_alone(self):
        f.make_syndicat(name="Taken")

        with pytest.raises(IntegrityError):
            with translate_integrity_errors({"some_other_constraint": lambda: InvalidInput("x")}):
                Syndicat.objects.create(name="taken")

    def test_exception_instances_are_refused_because_they_would_be_shared(self):
        with pytest.raises(TypeError):
            with translate_integrity_errors({"any": InvalidInput("Shared.")}):
                pass
