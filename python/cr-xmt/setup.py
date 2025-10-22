from setuptools import setup, find_packages

setup(
    name="cr-xmt",
    version="0.1.0",
    description="Extreme Mutation operator for Cosmic Ray",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "cosmic-ray",
        "parso>=0.8",
    ],
    entry_points={
        "cosmic_ray.operator_providers": [
            "cr_xmt = cr_xmt.provider:Provider",
        ]
    },
)