from EduVoteFlow.models import Candidate


def prepare_candidates(candidates: list[Candidate]):
    displayed_candidates = {}
    print(candidates)
    for candidate in candidates:
        dict_candidate = candidate.to_dict
        candidate_post = dict_candidate["post"]
        if candidate_post in displayed_candidates:
            displayed_candidates[candidate_post].append(dict_candidate)
        else:
            displayed_candidates[candidate_post] = [dict_candidate]
    return displayed_candidates
