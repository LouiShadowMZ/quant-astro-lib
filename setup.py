# setup.py

from setuptools import setup, find_packages

setup(
    name='quant-astro',  # pip 安装时使用的名字
    version='0.1.0',     # 版本号
    author='Lucius',    # 替换成你的名字
    author_email='你的邮箱@example.com', # 替换成你的邮箱
    description='一个用于量化占星研究的Python库',
    long_description=open('README.md').read() if open('README.md') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/LouiShadowMZ/quant-astro-lib.git', # 替换成你的 GitHub 仓库地址
    packages=find_packages(), # 自动寻找包 (会找到 quant_astro 文件夹)
    
    # 核心：告诉打包工具包含数据文件！
    package_data={
        'quant_astro': ['data/sub-sub.csv', 'ephe/*'],
    },
    include_package_data=True,
    
    # 列出这个库运行所需要的其他库
    install_requires=[
        'pyswisseph',
        'pytz',
        'pandas',
        'numpy',
        'ipython' # 因为 display 模块用到了 IPython
    ],
    
    # 其他元数据
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', # 你可以选择一个开源协议
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Astronomy',
    ],
    python_requires='>=3.8',
)