# setup.py

from setuptools import setup, find_packages
import os

# 使用更安全的方式读取 README.md 文件作为项目详细描述
long_description = ""
if os.path.exists('README.md'):
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()

setup(
    name='quant-astro',
    version='0.1.8',  # 与 quant_astro/__init__.py 的 __version__ 保持一致
    author='Lucius',
    author_email='kristenrobi85@gmail.com',
    description='一个用于量化占星研究的Python库。',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/LouiShadowMZ/quant-astro-lib.git',
    packages=find_packages(),
    
    # 包含了 data 和 ephe 目录下的所有文件
    package_data={
        'quant_astro': ['data/*', 'ephe/*'],
    },
    include_package_data=True,
    
    # 将 pyswisseph 替换为 pysweph；pytz 已用标准库 zoneinfo/timezone 替代，无需再声明
    install_requires=[
        'pysweph',
        'pandas',
        'numpy'
    ],
    
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Astronomy',
    ],
    python_requires='>=3.8',
)