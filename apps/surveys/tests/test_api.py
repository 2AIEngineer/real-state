import pytest

pytestmark = pytest.mark.django_db


def test_survey_from_draft_to_results_over_http(api, world):
    manager = api(world.manager, world.syndicat, world.prop)
    created = manager.post(
        "/api/v1/surveys/",
        {
            "title": "Lift",
            "target_roles": ["tenant"],
            "questions": [{"text": "Replace it?", "options": ["Yes", "No"]}],
        },
        format="json",
    )
    assert created.status_code == 201
    survey = created.json()
    assert (
        manager.post(f"/api/v1/surveys/{survey['id']}/publish/", {}, format="json").status_code
        == 200
    )

    question = survey["questions"][0]
    answered = api(world.tenant, world.syndicat, world.prop).post(
        f"/api/v1/surveys/{survey['id']}/responses/",
        {"answers": [{"question_id": question["id"], "option_id": question["options"][0]["id"]}]},
        format="json",
    )
    assert answered.status_code == 201

    assert (
        manager.post(f"/api/v1/surveys/{survey['id']}/close/", {}, format="json").status_code == 200
    )
    results = manager.get(f"/api/v1/surveys/{survey['id']}/results/")
    assert results.status_code == 200
