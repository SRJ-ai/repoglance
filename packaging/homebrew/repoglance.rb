# Homebrew formula template for repoglance.
#
# The `url`/`sha256` point at the PyPI sdist; bump both on each release
# (`brew fetch` prints the sha, or use `shasum -a 256`). The Python dependency
# `resources` are omitted here — generate them with:
#
#   brew install brew-pip-audit  # optional
#   brew update-python-resources Formula/repoglance.rb
#
# Then submit to a tap (e.g. SRJ-ai/homebrew-tap) so users can:
#
#   brew install SRJ-ai/tap/repoglance
class Repoglance < Formula
  include Language::Python::Virtualenv

  desc "Instant, gorgeous insight into any code repository"
  homepage "https://github.com/SRJ-ai/repoglance"
  url "https://files.pythonhosted.org/packages/source/r/repoglance/repoglance-0.4.0.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256"
  license "MIT"

  depends_on "python@3.12"

  # resource blocks for rich, click, lizard (+ transitive deps) go here —
  # generate them with `brew update-python-resources`.

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "repoglance, version", shell_output("#{bin}/repoglance --version")
  end
end
