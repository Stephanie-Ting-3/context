from os.path import join

from matplotlib.gridspec import GridSpec
from matplotlib.pyplot import close, figure, plot, show, subplot
from numpy import (argmax, argmin, asarray, cumsum, empty, linspace, log, sign,
                   where)
from pandas import DataFrame, Index, Series, concat
from seaborn import distplot, rugplot
from statsmodels.sandbox.distributions.extras import ACSkewT_gen

from .array_nd.array_nd.normalize_1d_array import normalize_1d_array
from .plot.plot.decorate import decorate
from .plot.plot.save_plot import save_plot
from .plot.plot.style import CMAP_CATEGORICAL_TAB20, FIGURE_SIZE
from .support.support.df import split_df
from .support.support.multiprocess import multiprocess
from .support.support.path import establish_path

# TODO: refactor


def fit_essentiality(feature_x_sample, file_path_prefix, features=(),
                     n_jobs=1):
    """
    Fit skew-t PDF to the distribution of each feature, gene.
    Arguments:
        feature_x_sample: DataFrame; (n_features, n_samples)
        file_path_prefix: str;
        features: iterable; selected features to fit
        n_jobs: int; number of jobs for parallel computing
    Returns:
        DataFrame; (n_features, 5 [N, DF, Shape, Location, Scale])
    """

    if len(features):  # Fit selected features
        is_ = Index(features) & feature_x_sample.index
        if len(is_):
            print('Fitting selected features: {} ...'.format(', '.join(is_)))
            feature_x_sample = feature_x_sample.ix[is_, :]
        else:
            raise ValueError('Selected features are not in indices.')
    else:  # Fit all features
        print('Fitting all features ...')

    print('Fitting with {} jobs ...'.format(n_jobs))
    f_x_f = concat(
        multiprocess(_fit_essentiality,
                     split_df(feature_x_sample, n_jobs), n_jobs))

    # Sort by shape
    f_x_f.sort_values('Shape', inplace=True)

    file_path = '{}skew_t_fit.txt'.format(file_path_prefix)
    establish_path(file_path)
    f_x_f.to_csv(file_path, sep='\t')

    return f_x_f


def _fit_essentiality(f_x_s):
    """
    """

    f_x_f = DataFrame(
        index=f_x_s.index, columns=['N', 'DF', 'Shape', 'Location', 'Scale'])

    for i, (f_i, f_v) in enumerate(f_x_s.iterrows()):
        print('Fitting {} (@{}/{}) ...'.format(f_i, i, f_x_s.shape[0]))

        # Fit skew-t PDF and save
        skew_t = ACSkewT_gen()
        f_v.dropna(inplace=True)
        df, shape, location, scale = skew_t.fit(f_v)
        f_x_f.ix[f_i, :] = f_v.size, df, shape, location, scale

    return f_x_f


def plot_essentiality(feature_x_sample,
                      feature_x_fit,
                      bar_df,
                      directory_path,
                      features=(),
                      enumerate_functions=False,
                      figure_size=FIGURE_SIZE,
                      n_x_grids=3000,
                      n_bins=50,
                      plot_fits=True,
                      show_plot=True):
    """
    Make essentiality plot for each gene.
    Arguments:
        feature_x_sample: DataFrame or str;
            (n_features, n_samples) or a file_path to a file
        feature_x_fit: DataFrame or str;
            (n_features, 5 (n, df, shape, location, scale)) or a file_path to a file
        bar_df: dataframe;
        directory_path: str;
            directory_path/essentiality_plots/feature<id>.png will be saved

        features: iterable; (n_selected_features)

        enumerate_functions: bool;

        figure_size: tuple; figure size
        n_x_grids: int; number of x grids
        n_bins: int; number of histogram bins
        plot_fits: bool; plot fitted lines or not
        show_plot: bool; show plot or not
    Returns:
        None
    """

    # ==========================================================================
    # Select features to plot
    # ==========================================================================
    if len(features):  # Plot only specified features
        is_ = [f for f in features if f in feature_x_sample.index]

        if len(is_):
            print('Plotting features: {} ...'.format(', '.join(is_)))
            feature_x_sample = feature_x_sample.ix[is_, :]
        else:
            raise ValueError('Specified features not found.')
    else:  # Plot all features
        print('Plotting all features ...')

    # ==========================================================================
    # Plot each feature
    # ==========================================================================
    for i, (f_i, f_v) in enumerate(feature_x_sample.iterrows()):
        print('Plotting {} (@{}/{}) ...'.format(f_i, i, feature_x_sample.shape[
            0]))

        # ======================================================================
        # Set up figure
        # ======================================================================
        # Initialize a figure
        fig = figure(figsize=figure_size)

        # Set figure grids
        n_rows = 10
        n_rows_graph = 5
        gridspec = GridSpec(n_rows, 1)

        # Make graph ax
        ax_graph = subplot(gridspec[:n_rows_graph, :])

        # Set bar axes
        ax_bar0 = subplot(gridspec[n_rows_graph + 1:n_rows_graph + 2, :])
        ax_bar1 = subplot(gridspec[n_rows_graph + 2:n_rows_graph + 3, :])
        ax_bar2 = subplot(gridspec[n_rows_graph + 3:n_rows_graph + 4, :])
        for ax in (ax_bar1, ax_bar0, ax_bar2):
            ax.spines['top'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for t in ax.get_xticklines():
                t.set_visible(False)
            for t in ax.get_xticklabels():
                t.set_visible(False)
            for t in ax.get_yticklines():
                t.set_visible(False)
            for t in ax.get_yticklabels():
                t.set_visible(False)

        # ======================================================================
        # Plot histogram
        # ======================================================================
        distplot(
            f_v,
            bins=n_bins,
            kde=False,
            norm_hist=True,
            hist_kws=dict(linewidth=0.92, color='#20d9ba', alpha=0.26),
            ax=ax_graph)

        # ==============================================================
        # Decorate
        # ==============================================================
        decorate(
            ax=ax_graph,
            style='white',
            title=f_i,
            xlabel='RNAi Score',
            ylabel='Frequency')

        # ==================================================================
        # Plot skew-t fit PDF
        # ==================================================================
        # Initialize a skew-t generator
        skew_t = ACSkewT_gen()

        # Set up grids
        grids = linspace(f_v.min(), f_v.max(), n_x_grids)

        # Parse fitted parameters
        n, df, shape, location, scale = feature_x_fit.ix[
            f_i, ['N', 'DF', 'Shape', 'Location', 'Scale']]
        fig.text(
            0.5,
            0.9,
            'N={:.0f}    DF={:.2f}    Shape={:.2f}    Location={:.2f}    '
            'Scale={:.2f}'.format(n, df, shape, location, scale),
            size=16,
            weight='bold',
            color='#220530',
            horizontalalignment='center')

        # Generate skew-t PDF
        skew_t_pdf = skew_t.pdf(grids, df, shape, loc=location, scale=scale)

        # Plot skew-t PDF
        line_kwargs = dict(linestyle='-', linewidth=2.6)
        ax_graph.plot(grids, skew_t_pdf, color='#20d9ba', **line_kwargs)

        # ==================================================================
        # Plot reflected skew-t PDF
        # ==================================================================
        # Generate skew-t PDF over reflected grids
        skew_t_pdf_r = skew_t.pdf(
            define_x_coordinates_for_reflection(skew_t_pdf, grids),
            df,
            shape,
            loc=location,
            scale=scale)

        # Plot over the original grids
        ax_graph.plot(grids, skew_t_pdf_r, color='#4e41d9', **line_kwargs)

        # ==================================================================
        # Plot essentiality indices from various functions
        # ==================================================================
        figure_size_ = (asarray(figure_size) * 0.7).astype(int)
        if enumerate_functions:
            functions = [
                # f1 /f2
                # Explode 'f1 / f2',
                # Signal at center 'log(f1 / f2)',
                # Explode 'where(f2 < f1, f1 / f2, 0)',
                # Not that good during entropy test 'where(f2 < f1, log(f1 /
                # f2), 0)',

                # - f2 /f1
                # Signal at center '-(f2 / f1)',
                # Signal at center '-log(f2 / f1)',
                # Spikes to 0 after center 'where(f2 < f1, -(f2 / f1), 0)',
                # == log(f1/ f2) 'where(f2 < f1, -log(f2 / f1), 0)',

                # carea1 / carea2
                # Explode 'carea1 / carea2',
                # Not that good during entropy test 'log(carea1 / carea2)',
                # Explode 'where(f2 < f1, carea1 / carea2, 0)',
                # 0ing abruptly drops 'where(f2 < f1, log(carea1 / carea2), 0)'

                # (f1 - f2) / f1
                # Better during only f2 < f1 '(f1 - f2) / f1',
                # Normalized same as not logging and raising to a power'log(
                # (f1 - f2) / f1 )',
                'where(f2 < f1, (f1 - f2) / f1, 0)',
                # Spikes to 0 after center 'where(f2 < f1, log( (f1 - f2) /
                # f1 ), 0)',

                # ((f1 - f2) / f1)^scale
                # Super negative '((f1 - f2) / f1)**{}'.format(scale),
                'where(f2 < f1log, ((f1 - f2) / f1)**{}, 0)'.format(scale),
                # log
                # Same as just log 'where(f2 < f1, log( ((f1 - f2) / f1)**{}
                # ), 0 )'.format(scale),

                # Hard to interpret # ((f1 - f2) / f1)^(1/scale)
                # log(-)=nan after center '((f1 - f2) / f1)**(1/{})'.format(
                # scale),
                # Widens wide 'where(f2 < f1, ((f1 - f2) / f1)**(1/{}),
                # 0)'.format(scale),

                # Hard to interpret # ((f1 - f2) / f1)^std(ei)
                # log(-)=nan after center '((f1 - f2) / f1)**(((f1 - f2) /
                # f1).std())',
                # Hard to interpret 'where(f2 < f1, ((f1 - f2) / f1)**(((f1 -
                #  f2) / f1).std()), 0) ',
                # Spikes to 0 after center 'where(f2 < f1, log( ((f1 - f2) /
                # f1)**(((f1 - f2) / f1).std()) ), 0) ',

                # Hard to interpret # ((f1 - f2) / f1)^(1/std(ei))
                # log(-)=nan after center '((f1 - f2) / f1)**(1/((f1 - f2) /
                # f1).std())',
                # Hard to interpret (best during entropy test)  'where(f2 <
                # f1, ((f1 - f2) / f1)**(1/((f1 - f2) / f1).std()), 0) ',
                # Same as just log 'where(f2 < f1, log( ((f1 - f2) / f1)**(
                # 1/((f1 - f2) / f1).std()) ), 0) ',
            ]
            eis = []

            # Plot each function
            for j, f in enumerate(functions):
                figure(figsize=figure_size_)

                # Compute essentiality index
                ei = _compute_essentiality_index(skew_t_pdf, skew_t_pdf_r, f,
                                                 ['+', '-'][shape > 0],
                                                 grids[1] - grids[0])

                c = CMAP_CATEGORICAL_TAB20(j / len(functions))
                eis.append((ei, c))

                plot(grids, ei, color=c, **line_kwargs)
                decorate(title=f)

            # Plot all functions
            figure(figsize=figure_size_)
            distplot(
                f_v,
                bins=n_bins,
                kde=False,
                norm_hist=True,
                hist_kws=dict(linewidth=0.92, color='#070707', alpha=0.26))
            for ei_, c in eis:
                plot(
                    grids, (ei_ - ei_.min()) /
                    (ei_.max() - ei_.min()) * skew_t_pdf.max(),
                    color=c,
                    linewidth=line_kwargs['linewidth'])
            decorate(title=f_i)

        # ==================================================================
        # Plot essentiality index (#fc154f)
        # ==================================================================
        ei = _compute_essentiality_index(
            skew_t_pdf, skew_t_pdf_r,
            'where(f2 < f1, ((f1 - f2) / f1)**{}, 0)'.format(scale),
            ['+', '-'][shape > 0], grids[1] - grids[0])
        ax_graph.plot(
            grids, (ei - ei.min()) / (ei.max() - ei.min()) * skew_t_pdf.max(),
            color='#fc154f',
            **line_kwargs)
        # ==================================================================
        # Plot bars
        # ==================================================================
        a_m_d = _get_amp_mut_del(bar_df, f_i)

        bar_specifications = [
            dict(vector=a_m_d.iloc[0, :], ax=ax_bar0, color='#9017e6'),
            dict(vector=a_m_d.iloc[1, :], ax=ax_bar1, color='#6410a0'),
            dict(vector=a_m_d.iloc[2, :], ax=ax_bar2, color='#470b72'),
        ]

        for spec in bar_specifications:
            v = spec['vector']
            ax = spec['ax']
            c = spec['color']
            rugplot(v * f_v, height=1, color=c, linewidth=2.4, ax=ax)
            decorate(ax=ax, ylabel=v.name[-3:])

        # ==================================================================
        # Save
        # ==================================================================
        save_plot(
            join(directory_path, 'essentiality_plots/{}.png'.format(f_i)))

        if show_plot:
            show()

        close()


def _get_amp_mut_del(gene_x_samples, gene):
    """
    Get AMP, MUT, and DEL information for a gene in the CCLEn.
    Arguments:
        gene_x_samples: DataFrame; (n_genes, n_samples)
        gene: str; gene index used in gene_x_sample
    Returns:
        DataFrame; (3 (AMP, MUT, DEL), n_samples)
    """

    # Amplification
    try:
        a = gene_x_samples.ix['{}_AMP'.format(gene), :]
    except KeyError:
        print('No amplification data for {}.'.format(gene))
        a = Series(index=gene_x_samples.columns, name='{}_AMP'.format(gene))

    # Mutation
    try:
        m = gene_x_samples.ix['{}_MUT'.format(gene), :]
    except KeyError:
        print('No mutation data for {}.'.format(gene))
        m = Series(index=gene_x_samples.columns, name='{}_MUT'.format(gene))

    # Deletion
    try:
        d = gene_x_samples.ix['{}_DEL'.format(gene), :]
    except KeyError:
        print('No deletion data for {}.'.format(gene))
        d = Series(index=gene_x_samples.columns, name='{}_DEL'.format(gene))

    return concat([a, m, d], axis=1).T


def make_essentiality_matrix(feature_x_sample,
                             feature_x_fit,
                             n_grids=3000,
                             function='scaled_fractional_difference',
                             factor=1):
    """

    Arguments:
        feature_x_sample: DataFrame; (n_features, n_samples)
        feature_x_fit: DataFrame;
        n_grids: int;
        function: str;
        factor: number;
    Returns:
        DataFrame; (n_features, n_samples)
    """

    print('\tApplying {} to each feature ...'.format(function))

    empty_ = empty(feature_x_sample.shape)

    skew_t = ACSkewT_gen()

    for i, (f_i, f_v) in enumerate(feature_x_sample.iterrows()):

        # Build skew-t PDF
        grids = linspace(f_v.min(), f_v.max(), n_grids)
        n, df, shape, location, scale = feature_x_fit.ix[i, :]
        skew_t_pdf = skew_t.pdf(grids, df, shape, loc=location, scale=scale)

        # Build reflected skew-t PDF
        skew_t_pdf_r = skew_t.pdf(
            define_x_coordinates_for_reflection(skew_t_pdf, grids),
            df,
            shape,
            loc=location,
            scale=scale)

        # Set up function
        if function.startswith('scaled_fractional_difference'):
            function = 'where(f2 < f1, ((f1 - f2) / f1)**{}, 0)'.format(scale)

        ei = _compute_essentiality_index(skew_t_pdf, skew_t_pdf_r, function,
                                         ['+',
                                          '-'][shape > 0], grids[1] - grids[0])

        ei = normalize_1d_array(ei, '0-1')

        empty_[i, :] = ei[[argmin(abs(grids - x))
                           for x in asarray(f_v)]] * sign(shape) * factor

    return DataFrame(
        empty_, index=feature_x_sample.index, columns=feature_x_sample.columns)


def _compute_essentiality_index(f1,
                                f2,
                                function,
                                area_direction=None,
                                delta=None):
    """
    Make a function from f1 and f2.
    Arguments:
        f1: array; function on the top
        f2: array; function at the bottom
        area_direction: str; {'+', '-'}
        function: str; ei = eval(function)
    Returns:
        array; ei
    """

    if 'area' in function:  # Compute cumulative area

        # Compute delta area
        darea1 = f1 / f1.sum() * delta
        darea2 = f2 / f2.sum() * delta

        # Compute cumulative area
        if area_direction == '+':  # Forward
            carea1 = cumsum(darea1)
            carea2 = cumsum(darea2)

        elif area_direction == '-':  # Reverse
            carea1 = cumsum(darea1[::-1])[::-1]
            carea2 = cumsum(darea2[::-1])[::-1]

        else:
            raise ValueError(
                'Unknown area_direction: {}.'.format(area_direction))

    # Compute essentiality index
    dummy = log
    dummy = where
    dummy = carea1
    dummy = carea2
    return eval(function)


def define_x_coordinates_for_reflection(function, x_grids):
    """
    Make x_grids for getting reflected function.
    Arguments:
        function: array; (1, x_grids.size)
        x_grids: array; (1, x_grids.size)
    Returns:
        array; (1, x_grids.size)
    """

    pivot_x = x_grids[argmax(function)]

    x_grids_for_reflection = empty(len(x_grids))
    for i, a_x in enumerate(x_grids):

        distance_to_reflecting_x = abs(a_x - pivot_x) * 2

        if a_x < pivot_x:  # Left of the pivot x
            x_grids_for_reflection[i] = a_x + distance_to_reflecting_x

        else:  # Right of the pivot x
            x_grids_for_reflection[i] = a_x - distance_to_reflecting_x

    return x_grids_for_reflection
