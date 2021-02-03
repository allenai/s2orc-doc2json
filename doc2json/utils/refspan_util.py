from typing import List, Tuple


def replace_refspans(
    spans_to_replace: List[Tuple[int, int, str, str]],
    full_string: str,
    pre_padding: str = "",
    post_padding: str = "",
    btwn_padding: str = ", "
) -> str:
    """
    For each span within the full string, replace that span with new text
    :param spans_to_replace: list of tuples of form (start_ind, end_ind, span_text, new_substring)
    :param full_string:
    :param pre_padding:
    :param post_padding:
    :param btwn_padding:
    :return:
    """
    # assert all spans are equal to full_text span
    assert all([full_string[start:end] == span for start, end, span, _ in spans_to_replace])

    # assert none of the spans start with the same start ind
    start_inds = [rep[0] for rep in spans_to_replace]
    assert len(set(start_inds)) == len(start_inds)

    # sort by start index
    spans_to_replace.sort(key=lambda x: x[0])

    # form strings for each span group
    for i, entry in enumerate(spans_to_replace):
        start, end, span, new_string = entry

        # skip empties
        if end <= 0:
            continue

        # compute shift amount
        shift_amount = len(new_string) - len(span) + len(pre_padding) + len(post_padding)

        # shift remaining appropriately
        for ind in range(i + 1, len(spans_to_replace)):
            next_start, next_end, next_span, next_string = spans_to_replace[ind]
            # skip empties
            if next_end <= 0:
                continue
            # if overlap between ref span and current ref span, remove from replacement
            if next_start < end:
                next_start = 0
                next_end = 0
                next_string = ""
            # if ref span abuts previous reference span
            elif next_start == end:
                next_start += shift_amount
                next_end += shift_amount
                next_string = btwn_padding + pre_padding + next_string + post_padding
            # if ref span starts after, shift starts and ends
            elif next_start > end:
                next_start += shift_amount
                next_end += shift_amount
                next_string = pre_padding + next_string + post_padding
            # save adjusted span
            spans_to_replace[ind] = (next_start, next_end, next_span, next_string)

    spans_to_replace = [entry for entry in spans_to_replace if entry[1] > 0]
    spans_to_replace.sort(key=lambda x: x[0])

    # apply shifts in series
    for start, end, span, new_string in spans_to_replace:
        assert full_string[start:end] == span
        full_string = full_string[:start] + new_string + full_string[end:]

    return full_string


def sub_spans_and_update_indices(
    spans_to_replace: List[Tuple[int, int, str, str]],
    full_string: str
) -> Tuple[str, List]:
    """
    Replace all spans and recompute indices
    :param spans_to_replace:
    :param full_string:
    :return:
    """
    # TODO: check no spans overlapping
    # TODO: check all spans well-formed

    # assert all spans are equal to full_text span
    assert all([full_string[start:end] == token for start, end, token, _ in spans_to_replace])

    # assert none of the spans start with the same start ind
    start_inds = [rep[0] for rep in spans_to_replace]
    assert len(set(start_inds)) == len(start_inds)

    # sort by start index
    spans_to_replace.sort(key=lambda x: x[0])

    # compute offsets for each span
    new_spans = [[start, end, token, surface, 0] for start, end, token, surface in spans_to_replace]
    for i, entry in enumerate(spans_to_replace):
        start, end, token, surface = entry
        new_end = start + len(surface)
        offset = new_end - end
        new_spans[i][1] += offset
        for new_span_entry in new_spans[i+1:]:
            new_span_entry[4] += offset

    # generate new text and create final spans
    new_text = replace_refspans(spans_to_replace, full_string, btwn_padding="")
    new_spans = [(start + offset, end + offset, token, surface) for start, end, token, surface, offset in new_spans]

    return new_text, new_spans


