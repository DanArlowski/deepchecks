# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module containing html serializer for the CheckResult type."""
import textwrap
import typing as t

from plotly.io import to_html
from typing_extensions import Literal

from deepchecks.core import check_result as check_types
from deepchecks.core.serialization.abc import ABCDisplayItemsHandler, HtmlSerializer
from deepchecks.core.serialization.common import (aggregate_conditions, form_output_anchor, plotlyjs_script,
                                                  requirejs_script)
from deepchecks.core.serialization.dataframe.html import DataFrameSerializer as DataFrameHtmlSerializer
from deepchecks.utils.html import imagetag

__all__ = ['CheckResultSerializer']


CheckResultSection = t.Union[
    Literal['condition-table'],
    Literal['additional-output'],
]


class CheckResultSerializer(HtmlSerializer['check_types.CheckResult']):
    """Serializes any CheckResult instance into HTML format.

    Parameters
    ----------
    value : CheckResult
        CheckResult instance that needed to be serialized.
    """

    def __init__(self, value: 'check_types.CheckResult', **kwargs):
        if not isinstance(value, check_types.CheckResult):
            raise TypeError(
                f'Expected "CheckResult" but got "{type(value).__name__}"'
            )
        self.value = value

    def serialize(
        self,
        output_id: t.Optional[str] = None,
        check_sections: t.Optional[t.Sequence[CheckResultSection]] = None,
        full_html: bool = False,
        include_requirejs: bool = False,
        include_plotlyjs: bool = True,
        connected: bool = True,
        **kwargs
    ) -> str:
        """Serialize a CheckResult instance into HTML format.

        Parameters
        ----------
        output_id : Optional[str], default None
            unique output identifier that will be used to form anchor links
        check_sections : Optional[Sequence[Literal['condition-table', 'additional-output']]], default None
            sequence of check result sections to include into the output,
            in case of 'None' all sections will be included
        full_html : bool, default False
            whether to return a fully independent HTML document or only CheckResult content
        include_requirejs : bool, default False
            whether to include requirejs library into output or not
        include_plotlyjs : bool, default True
            whether to include plotlyjs library into output or not
        connected : bool, default True
            whether to use CDN to load js libraries or to inject their code into output

        Returns
        -------
        str
        """
        if full_html is True:
            include_plotlyjs = True
            include_requirejs = True
            connected = False

        sections_to_include = verify_include_parameter(check_sections)
        sections = [self.prepare_header(output_id), self.prepare_summary()]

        if 'condition-table' in sections_to_include:
            sections.append(''.join(self.prepare_conditions_table(output_id=output_id)))

        if 'additional-output' in sections_to_include:
            sections.append(''.join(self.prepare_additional_output(output_id)))

        plotlyjs = plotlyjs_script(connected) if include_plotlyjs is True else ''
        requirejs = requirejs_script(connected) if include_requirejs is True else ''

        if full_html is False:
            return ''.join([requirejs, plotlyjs, *sections])

        # TODO: use some style to make it pretty
        return textwrap.dedent(f"""
            <html>
            <head><meta charset="utf-8"/></head>
            <body>
                {''.join([requirejs, plotlyjs, *sections])}
            </body>
            </html>
        """)

    def prepare_header(self, output_id: t.Optional[str] = None) -> str:
        """Prepare the header section of the html output."""
        header = self.value.get_header()
        header = f'<b>{header}</b>'
        if output_id is not None:
            check_id = self.value.get_check_id(output_id)
            return f'<h4 id="{check_id}">{header}</h4>'
        else:
            return f'<h4>{header}</h4>'

    def prepare_summary(self) -> str:
        """Prepare the summary section of the html output."""
        return f'<p>{self.value.get_metadata()["summary"]}</p>'

    def prepare_conditions_table(
        self,
        max_info_len: int = 3000,
        include_icon: bool = True,
        include_check_name: bool = False,
        output_id: t.Optional[str] = None,
    ) -> str:
        """Prepare the conditions table of the html output.

        Parameters
        ----------
        max_info_len : int, default 3000
            max length of the additional info
        include_icon : bool , default: True
            if to show the html condition result icon or the enum
        include_check_name : bool, default False
            whether to include check name into dataframe or not
        output_id : Optional[str], default None
            unique output identifier that will be used to form anchor links

        Returns
        -------
        str
        """
        if not self.value.have_conditions():
            return ''
        table = DataFrameHtmlSerializer(aggregate_conditions(
            self.value,
            max_info_len=max_info_len,
            include_icon=include_icon,
            include_check_name=include_check_name,
            output_id=output_id
        )).serialize()
        return f'<h5><b>Conditions Summary</b></h5>{table}'

    def prepare_additional_output(
        self,
        output_id: t.Optional[str] = None
    ) -> t.List[str]:
        """Prepare the display content of the html output.

        Parameters
        ----------
        output_id : Optional[str], default None
            unique output identifier that will be used to form anchor links

        Returns
        -------
        str
        """
        return DisplayItemsHandler.handle_display(
            self.value.display,
            output_id=output_id
        )


class DisplayItemsHandler(ABCDisplayItemsHandler):
    """Auxiliary class to decouple display handling logic from other functionality."""

    @classmethod
    def handle_display(
        cls,
        display: t.List['check_types.TDisplayItem'],
        output_id: t.Optional[str] = None,
        **kwargs
    ) -> t.List[str]:
        """Serialize CheckResult display items into HTML.

        Parameters
        ----------
        display : List[Union[Callable, str, DataFrame, Styler]]
            list of display items
        output_id : Optional[str], default None
            unique output identifier that will be used to form anchor links

        Returns
        -------
        List[str]
        """
        output = [
            cls.header(),
            *super().handle_display(display, **{'output_id': output_id, **kwargs})
        ]

        if len(display) == 0:
            output.append(cls.empty_content_placeholder())

        if output_id is not None:
            output.append(cls.go_to_top_link(output_id))

        return output

    @classmethod
    def header(cls) -> str:
        """Return header section."""
        return '<h5><b>Additional Outputs</b></h5>'

    @classmethod
    def empty_content_placeholder(cls) -> str:
        """Return placeholder in case of content absence."""
        return '<p><b>&#x2713;</b>Nothing to display</p>'

    @classmethod
    def go_to_top_link(cls, output_id: str) -> str:
        """Return 'Go To Top' link."""
        href = form_output_anchor(output_id)
        return f'<br><a href="#{href}" style="font-size: 14px">Go to top</a>'

    @classmethod
    def handle_string(cls, item, index, **kwargs) -> str:
        """Handle textual item."""
        return f'<div>{item}</div>'

    @classmethod
    def handle_dataframe(cls, item, index, **kwargs) -> str:
        """Handle dataframe item."""
        return DataFrameHtmlSerializer(item).serialize()

    @classmethod
    def handle_callable(cls, item, index, **kwargs) -> str:
        """Handle callable."""
        images = super().handle_callable(item, index, **kwargs)
        tags = []

        for buffer in images:
            buffer.seek(0)
            tags.append(imagetag(buffer.read()))
            buffer.close()

        return ''.join(tags)

    @classmethod
    def handle_figure(cls, item, index, **kwargs) -> str:
        """Handle plotly figure item."""
        post_script = textwrap.dedent("""
            var gd = document.getElementById('{plot_id}');
            var x = new MutationObserver(function (mutations, observer) {{
                    var display = window.getComputedStyle(gd).display;
                    if (!display || display === 'none') {{
                        console.log([gd, 'removed!']);
                        Plotly.purge(gd);
                        observer.disconnect();
                    }}
            }});

            // Listen for the removal of the full notebook cells
            var notebookContainer = gd.closest('#notebook-container');
            if (notebookContainer) {{
                x.observe(notebookContainer, {childList: true});
            }}

            // Listen for the clearing of the current output cell
            var outputEl = gd.closest('.output');
            if (outputEl) {{
                x.observe(outputEl, {childList: true});
            }}
        """)
        return to_html(
            item,
            auto_play=False,
            include_plotlyjs='require',
            post_script=post_script,
            full_html=False,
            default_width='100%',
            default_height=525,
            validate=True,
        )


def verify_include_parameter(
    include: t.Optional[t.Sequence[CheckResultSection]] = None
) -> t.Set[CheckResultSection]:
    """Verify CheckResultSection sequence."""
    sections = t.cast(
        t.Set[CheckResultSection],
        {'condition-table', 'additional-output'}
    )

    if include is None:
        sections_to_include = sections
    elif len(include) == 0:
        raise ValueError('include parameter cannot be empty')
    else:
        sections_to_include = set(include)

    if len(sections_to_include.difference(sections)) > 0:
        raise ValueError(
            'include parameter must contain '
            'Union[Literal["condition-table"], Literal["additional-output"]]'
        )

    return sections_to_include
