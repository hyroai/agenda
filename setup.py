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
        "computation-graph>=32",
        "immutables",
        "Jpype1==0.6.3",
        "dataclasses",
        "duckling",
        "httpx",
        "pyap",
        "pygrahpviz",
        "spacy",
        "asyncio",
        "fastapi",
        "uvicorn==0.15.0",
        "starlette",
        "toposort",
    ],
    package_data={"": [], "agenda": ["py.typed"]},
    include_package_data=True,
)
