import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


WINDOWS_SOFFICE_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "LibreOffice" / "program" / "soffice.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "LibreOffice" / "program" / "soffice.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LibreOffice" / "program" / "soffice.exe",
]


def find_executable(name, extra_candidates=()):
    found = shutil.which(name)
    if found:
        return Path(found)
    for candidate in extra_candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def run_checked(args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        command = " ".join(str(arg) for arg in args)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}:\n"
            f"{command}\n\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def convert_docx_to_pdf(docx_path, output_dir, soffice):
    profile_dir = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    profile_uri = profile_dir.as_uri()
    args = [
        str(soffice),
        f"-env:UserInstallation={profile_uri}",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(docx_path),
    ]
    result = run_checked(args)
    pdf_path = output_dir / f"{docx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError(
            "LibreOffice finished without producing the expected PDF.\n"
            f"Expected: {pdf_path}\n\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return pdf_path


def render_pdf_to_png(pdf_path, output_dir, pdftoppm, prefix):
    for old_page in output_dir.glob(f"{prefix}-*.png"):
        old_page.unlink()
    page_prefix = output_dir / prefix
    args = [str(pdftoppm), "-png", "-r", "160", str(pdf_path), str(page_prefix)]
    run_checked(args)
    pages = sorted(output_dir.glob(f"{prefix}-*.png"))
    if not pages:
        raise RuntimeError(f"pdftoppm finished without producing PNG pages in {output_dir}")
    return pages


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render a DOCX to PDF and page PNGs using LibreOffice/soffice and pdftoppm."
    )
    parser.add_argument("docx", type=Path, help="Input .docx file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the PDF and rendered PNG pages",
    )
    parser.add_argument("--soffice", type=Path, default=None, help="Explicit path to soffice.exe")
    parser.add_argument("--pdftoppm", type=Path, default=None, help="Explicit path to pdftoppm.exe")
    parser.add_argument("--prefix", default="page", help="PNG page filename prefix")
    return parser.parse_args()


def main():
    args = parse_args()
    docx_path = args.docx.resolve()
    if not docx_path.exists():
        raise SystemExit(f"Input DOCX does not exist: {docx_path}")

    output_dir = (args.output_dir or docx_path.with_suffix("").with_name(docx_path.stem + "_rendered")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    soffice = args.soffice or find_executable("soffice", WINDOWS_SOFFICE_CANDIDATES)
    if not soffice:
        raise SystemExit(
            "Could not find LibreOffice soffice. Install LibreOffice or pass --soffice "
            r'"C:\Program Files\LibreOffice\program\soffice.exe".'
        )

    pdftoppm = args.pdftoppm or find_executable("pdftoppm")
    if not pdftoppm:
        raise SystemExit("Could not find pdftoppm. Install Poppler or pass --pdftoppm.")

    pdf_path = convert_docx_to_pdf(docx_path, output_dir, soffice)
    pages = render_pdf_to_png(pdf_path, output_dir, pdftoppm, args.prefix)

    print(f"PDF: {pdf_path}")
    print(f"Rendered pages: {len(pages)}")
    for page in pages:
        print(page)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
