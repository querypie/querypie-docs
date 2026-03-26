from converter.core import ConfluenceToMarkdown
from mdx_to_storage import emit_document, parse_mdx


def _roundtrip_mdx_via_storage_xhtml(mdx: str, tmp_path) -> str:
    xhtml = emit_document(parse_mdx(mdx))
    converter = ConfluenceToMarkdown(xhtml)
    converter.load_attachments(
        input_dir=str(tmp_path),
        output_dir="/images",
        public_dir=str(tmp_path),
        skip_image_copy=True,
    )
    return converter.as_markdown()


def test_figure_width_survives_storage_roundtrip(tmp_path):
    mdx = """<figure>
  <img src="/images/path/sample.png" alt="Sample" width="700">
</figure>
"""

    markdown = _roundtrip_mdx_via_storage_xhtml(mdx, tmp_path)

    assert 'width="700"' in markdown
    assert 'src="/images/sample.png"' in markdown


def test_list_item_figure_width_survives_storage_roundtrip(tmp_path):
    mdx = """1. Text <br/>
  <figure data-layout="center" data-align="center">
  <img src="/images/path/sample-image.png" alt="sample-image.png" width="712" />
  </figure>
"""

    markdown = _roundtrip_mdx_via_storage_xhtml(mdx, tmp_path)

    assert 'width="712"' in markdown
    assert 'src="/images/sample-image.png"' in markdown
