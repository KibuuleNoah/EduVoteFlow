from EduVoteFlow.models import Candidate


def prepare_candidates(candidates: list[Candidate]) -> dict:
    """
    Groups candidates bases on their post
    candidate on the same post will be grouped
    in the same list keyed by their post

    :param candidates : list of candidates class instaces
    :type candidates : list
    :returns : a dict of grouped candidates by post
    :rtype : dict
    """
    displayed_candidates = {}
    for candidate in candidates:
        # coverts candidate class object to dict
        dict_candidate = candidate.to_dict
        # get candidate's post
        candidate_post = dict_candidate["post"]
        # if post exists add candidate to list
        if candidate_post in displayed_candidates:
            displayed_candidates[candidate_post].append(dict_candidate)
        # else create and add to it
        else:
            displayed_candidates[candidate_post] = [dict_candidate]
    return displayed_candidates
