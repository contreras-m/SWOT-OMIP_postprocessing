from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

from matplotlib.ticker import FuncFormatter
def plot_psd(ax, freqs, psds, unit, psd_labels, title=None,legend=True,loc_leg="best",bba_leg=(1,1), xtick_show=True, ytick_show=True, xlabel_upper=True,xlabel_lower=True, ylabel=True, savefig=False, filename=None,plot_transparent=False, colors=None, lsts=None, max_horizontal_gridsize=None, wavelength_ticks = np.array([5, 10, 25, 50, 100, 1000]),slope=True,scaleX='log', scaleY='log',
             ylabelname=f"PSD [m2/(cy/km)$]",xlabelname_bottom="Wavenumber [$cy/km$]", xlabelname_upper="Wavelength [$km$]"):
    """
    Plots the Power Spectral Density (PSD) on a logarithmic scale.
    
    The function plots the PSD on the given axes, `ax`. The plot is on a logarithmic scale 
    for both x and y axes. The function can handle one or two PSD arrays. If provided, 
    it adds labels and a title to the plot. It also includes reference lines for $k^{-2}$ 
    and $k^{-5}$ slopes.

    The function adds grid lines, legends, and adjusts axis labels and ticks for better readability.

    If `freqs` or `psd1` are empty, the function prints an error message and returns 
    without plotting.
    
    Parameters
    ------------
    ax: matplotlib.axes.Axes
        The axes on which to plot the PSD. 
    freqs: np.ndarray
        A numpy array containing frequency values.
    psds: [np.ndarray, ...] | np.ndarray
        A list of numpy array or a single numpy array of PSD values corresponding to `freqs`.
    unit: str
        Unit of the physical quantity for which the PSD was computed.
    psd_labels: [str, ...] | str, optional
        A list of labels or a single label for the PDS array(s).
    title: str, optional
        Title of the plot.
    savefig: bool 
        True to save the figure, False otherwise
    filename: str or None
        Name of the file to save the figure, default is 'figure.png'
    plot_transparent: bool
        True to display the figure with a transparent background, False otherwise
    """
    psds = np.asarray(psds)

    if psds.ndim == 1:
        psds = [psds]
        if psd_labels is not None:
            psd_labels = [psd_labels]

    if psd_labels is None:
        psd_labels = [None] * len(psds)
    #psd_labels = psd_labels[0]
    n_psds = np.shape(psds)[0] #if isinstance(psds, np.ndarray) else len(psds)
        # Normalize colors
    if colors is None:
        colors = [None] * n_psds
    elif isinstance(colors, str):
        colors = [colors] * n_psds
    elif len(colors) != n_psds:
       raise ValueError("Length of 'colors' must match number of PSDs")

    if lsts is None:
        lsts= [None] * n_psds
    elif isinstance(lsts, str):
        lsts = [lsts] * n_psds
    elif len(lsts) != n_psds:
       raise ValueError("Length of 'colors' must match number of PSDs")
        
       # Validate grid size list
    if max_horizontal_gridsize is not None and len(max_horizontal_gridsize) != len(psds):
        raise ValueError("Length of 'max_horizontal_gridsize' must match number of PSDs")

    # --- Plot PSDs ---
    for i, (psd, label, color,lst) in enumerate(zip(psds, psd_labels, colors,lsts)):
        psd = np.array(psd)
        if max_horizontal_gridsize is not None:
            mask = (1 / freqs) >= (2 * max_horizontal_gridsize[i])
            freqs_to_plot = freqs[mask]       
            psd_to_plot = psd[mask]
        else:
            freqs_to_plot = freqs
            psd_to_plot = psd


        ax.plot(freqs_to_plot, psd_to_plot, label=label, color=color,linestyle=lst,
                linewidth=2)
        ax.set_xscale(scaleX)     # logarithmic x-axis
        ax.set_yscale(scaleY)

    #ax.set_ylim(1e-7, 1e2)
    if ylabel==True:
        ax.set_ylabel(ylabelname, fontsize=8, fontweight="bold", color="black")

    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()


    # filters out zero frequencies
    non_zero_freqs = freqs[freqs != 0]

    # k^-2 & k^-5
    if slope==True:
    # k^-2 & k^-5
        k_2 = non_zero_freqs ** -2 * (psds[0][0] / (non_zero_freqs[0] ** -2))  # Scale according to the first PSD value
        k_3 = non_zero_freqs ** -3 * (psds[0][0] / (non_zero_freqs[0] ** -3))
        k_5 = non_zero_freqs ** -5 * (psds[0][0] / (non_zero_freqs[0] ** -5))

        ax.plot(non_zero_freqs, k_2*1, color="black",linestyle="dotted", label="$k^{-2}$")  # 30 to fix the line
        ax.plot(non_zero_freqs, k_3*1.5, color="dimgray",linestyle="dotted", label="$k^{-3}$")  # 1e6 to fix the line
        ax.plot(non_zero_freqs, k_5*10, color="darkgray",linestyle="dotted", label="$k^{-5}$")  # 1e6 to fix the line

        ax.set_xscale(scaleX)     # logarithmic x-axis
        ax.set_yscale(scaleY)





# ==========================================================
# BOTTOM AXIS: wavenumber
# ==========================================================


    # Angular wavenumber corresponding to them
    k_ticks = 1 / wavelength_ticks

    # Axis limits
    ax.set_xlim(k_ticks[-1], k_ticks[0])


    # ---- bottom ticks: ONLY these ticks -----------------------

    ax.xaxis.set_major_locator(FixedLocator(k_ticks))
    ax.xaxis.set_minor_locator(NullLocator())

    ax.set_xticklabels([
        f"{k:.3f}" for k in k_ticks
    ])

    #ax.set_xlabel(r"Wavenumber [rad km$^{-1}$]")
    ax.xaxis.set_ticks_position("bottom")
    ax.xaxis.set_label_position("bottom")

    if xlabel_lower==True:
        ax.set_xlabel(xlabelname_bottom, fontsize=8, fontweight="bold", color="black")

# ==========================================================
# TOP AXIS: wavelength
# ==========================================================


    ax_top = ax.twiny()

    # EXACTLY the same coordinate system
    ax_top.set_xscale("log")
    ax_top.set_xlim(ax.get_xlim())


    # ---- top ticks: SAME POSITIONS ----------------------------

    ax_top.xaxis.set_major_locator(FixedLocator(k_ticks))
    ax_top.xaxis.set_minor_locator(NullLocator())

    # But different labels
    ax_top.set_xticklabels([
        f"{w:.0f}" for w in wavelength_ticks
    ])

    #ax_top.set_xlabel("Wavelength [km]")

    ax.grid(True, which="both")
    ax.tick_params(axis="x", labelsize=7)
    ax_top.tick_params(axis="x", labelsize=7)

    # Upper axis
    ax_top.tick_params(
        axis="x",
        labelsize=7,
        pad=2
    )


    if xlabel_upper==True:
        ax_top.set_xlabel(
            xlabelname_upper,
            fontweight="bold",
            fontsize=8,
            labelpad=8
        )

# ==========================================================
# Legend and extras
# ==========================================================


    if legend==True:
        handles, labels = ax.get_legend_handles_labels()

        # Remove duplicated labels
        unique = dict(zip(labels, handles))

        ax.legend(
            unique.values(),
            unique.keys(),
            bbox_to_anchor=bba_leg
        )

    # Set the title if provided
    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", color="black")

    if xtick_show==False:
        ax.set_xticks([])
        ax2.set_xticks([])

    if ytick_show==False:
        ax.set_yticks([])
    
    # Handle saving the figure if savefig is True
    if savefig:
        if filename is None:
            # Use default filename if none is provided
            filename = "figure.png"
        if plot_transparent:
            plt.savefig(filename,dpi=300,transparent=plot_transparent)
        else:
            plt.savefig(filename,dpi=300)