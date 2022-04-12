import setuptools

with open("README.md", "r") as fh:
    _LONG_DESCRIPTION = fh.read()


setuptools.setup(
    name="agenda",
    version="0.0.1",
    long_description=_LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=setuptools.find_namespace_packages(),
    zip_safe=False,
    install_requires=[
        "gamla>=121",
        "computation-graph>=38",
        "pytest-asyncio>=0.17",
        "dataclasses",
        "dateparser",
        "httpx",
        "pyap",
        "spacy",
        "asyncio",
        "fastapi",
        "uvicorn[standard]",
        "starlette",
        "toposort",
        "number_parser",
    ],
    package_data={"": [], "agenda": ["py.typed"]},
    include_package_data=True,
    extras_require={"dev": ["pytest", "pre-commit"]},
    entry_points={"console_scripts": ["agenda = config_to_bot.main:main"]},
)
