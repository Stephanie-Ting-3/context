from os.path import join

from pandas import DataFrame, Series, concat
from statsmodels.sandbox.distributions.extras import ACSkewT_gen

from .compute_context import compute_context
from .support.support.df import split_df
from .support.support.multiprocess import multiprocess
from .support.support.path import establish_path


def make_context_matrix_and_summarize_context(
        feature_x_sample,
        n_job=1,
        feature_x_skew_t_pdf_fit_parameter=None,
        fit_fixed_location=None,
        fit_fixed_scale=None,
        fit_initial_location=None,
        fit_initial_scale=None,
        n_grid=1000,
        degree_of_freedom_for_tail_reduction=10e8,
        global_location=None,
        global_scale=None,
        directory_path=None):
    """
    Make context matrix and summarize context.
    Arguments:
        feature_x_sample (DataFrame): (n_feature, n_sample, )
        n_job (int):
        feature_x_skew_t_pdf_fit_parameter (DataFrame):
        fit_fixed_location (float):
        fit_fixed_scale (float):
        fit_initial_location (float):
        fit_initial_scale (float):
        n_grid (int):
        degree_of_freedom_for_tail_reduction (float):
        global_location (float):
        global_scale (float):
        directory_path (str):
    Returns:
        DataFrame: (n_feature, n_sample, )
        Series: (n_feature, )
    """

    returns = multiprocess(
        _make_context_matrix_and_summarize_context,
        ((
            feature_x_sample_,
            feature_x_skew_t_pdf_fit_parameter,
            fit_fixed_location,
            fit_fixed_scale,
            fit_initial_location,
            fit_initial_scale,
            n_grid,
            degree_of_freedom_for_tail_reduction,
            global_location,
            global_scale, )
         for feature_x_sample_ in split_df(feature_x_sample, n_job)), n_job)

    context__feature_x_sample = concat((r[0] for r in returns))
    feature_context_summary = concat((r[1] for r in returns))

    if directory_path:
        establish_path(directory_path, 'directory')

        context__feature_x_sample.to_csv(
            join(directory_path, 'context__feature_x_sample.tsv'), sep='\t')

        feature_context_summary.to_csv(
            join(directory_path, 'feature_context_summary.tsv'),
            header=True,
            sep='\t')

    return context__feature_x_sample, feature_context_summary


def _make_context_matrix_and_summarize_context(
        feature_x_sample, feature_x_skew_t_pdf_fit_parameter,
        fit_fixed_location, fit_fixed_scale, fit_initial_location,
        fit_initial_scale, n_grid, degree_of_freedom_for_tail_reduction,
        global_location, global_scale):
    """
    Make context matrix and summarize context.
    Arguments:
        feature_x_sample (DataFrame): (n_feature, n_sample, )
        feature_x_skew_t_pdf_fit_parameter (DataFrame):
        fit_fixed_location (float):
        fit_fixed_scale (float):
        fit_initial_location (float):
        fit_initial_scale (float):
        n_grid (int):
        degree_of_freedom_for_tail_reduction (float):
        global_location (float):
        global_scale (float):
    Returns:
        DataFrame: (n_feature, n_sample, )
        Series: (n_feature, )
    """

    skew_t_model = ACSkewT_gen()

    context__feature_x_sample = DataFrame(
        index=feature_x_sample.index,
        columns=feature_x_sample.columns,
        dtype=float)
    context__feature_x_sample.index.name = 'Feature'

    feature_context_summary = Series(
        index=context__feature_x_sample.index,
        name='Context Summary',
        dtype=float)

    n_per_log = max(feature_x_sample.shape[0] // 10, 1)

    for i, (
            feature_index,
            feature_vector, ) in enumerate(feature_x_sample.iterrows()):

        if i % n_per_log == 0:
            print('({}/{}) {} ...'.format(i + 1, feature_x_sample.shape[0],
                                          feature_index))

        if feature_x_skew_t_pdf_fit_parameter is None:
            location = scale = degree_of_freedom = shape = None
        else:
            location, scale, degree_of_freedom, shape = feature_x_skew_t_pdf_fit_parameter.loc[
                feature_index, [
                    'Location',
                    'Scale',
                    'Degree of Freedom',
                    'Shape',
                ]]

        context_dict = compute_context(
            feature_vector,
            skew_t_model=skew_t_model,
            location=location,
            scale=scale,
            degree_of_freedom=degree_of_freedom,
            shape=shape,
            fit_fixed_location=fit_fixed_location,
            fit_fixed_scale=fit_fixed_scale,
            fit_initial_location=fit_initial_location,
            fit_initial_scale=fit_initial_scale,
            n_grid=n_grid,
            degree_of_freedom_for_tail_reduction=
            degree_of_freedom_for_tail_reduction,
            global_location=global_location,
            global_scale=global_scale)

        context__feature_x_sample.loc[feature_index] = context_dict[
            'context_indices_like_array']

        feature_context_summary[feature_index] = context_dict[
            'context_summary']

    return context__feature_x_sample, feature_context_summary
