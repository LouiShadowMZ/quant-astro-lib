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
    version='0.1.4',  # <-- 版本号已更新
    author='Lucius',
    author_email='kristenrobi85@gmail.com', # 建议更新为您的真实邮箱
    description='一个用于量化占星研究的Python库。', # 描述可以更具体一些
    long_description=long_description, # <-- 使用了更安全的读取方式
    long_description_content_type='text/markdown',
    url='https://github.com/LouiShadowMZ/quant-astro-lib.git',
    packages=find_packages(),
    
    # 包含了 data 和 ephe 目录下的所有文件，更具扩展性
    package_data={
        'quant_astro': ['data/*', 'ephe/*'],
    },
    include_package_data=True,
    
    # 确认所有依赖项都已列出
    install_requires=[
        'pyswisseph',
        'pytz',
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