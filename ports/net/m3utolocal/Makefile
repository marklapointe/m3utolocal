PORTNAME=	m3utolocal
DISTVERSION=	1.1.0
CATEGORIES=	net

MAINTAINER=	mark@cloudbsd.org
COMMENT=	Search M3U playlists and download VOD files to a local library
WWW=		https://github.com/marklapointe/m3utolocal

LICENSE=	BSD2CLAUSE
LICENSE_FILE=	${WRKSRC}/LICENSE

RUN_DEPENDS=	${PYTHON_PKGNAMEPREFIX}requests>=2.31.0:www/py-requests@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}textual>=0.80.0:textproc/py-textual@${PY_FLAVOR}

USES=		python shebangfix
USE_PYTHON=	flavors

# Development: make LOCAL_SRC_PATH=/path/to/checkout -DLOCAL_SRC stage
# Release: fetch m3utolocal-1.1.0.tar.gz (see distinfo) from GitHub Releases
#   or place the tarball in ${DISTDIR} and run: make checksum
.if defined(LOCAL_SRC) || defined(LOCAL_SRC_PATH)
NO_CHECKSUM=	yes
DISTFILES=
.  if defined(LOCAL_SRC_PATH)
WRKSRC=		${LOCAL_SRC_PATH}
.  else
WRKSRC=		${.CURDIR}/../../..
.  endif
.else
MASTER_SITES=	https://github.com/marklapointe/m3utolocal/releases/download/v${DISTVERSION}/
DISTNAME=	m3utolocal-${DISTVERSION}
.endif

SHEBANG_FILES=	main.py

NO_ARCH=	yes
NO_BUILD=	yes

.if defined(LOCAL_SRC) || defined(LOCAL_SRC_PATH)
do-fetch:
	@${DO_NADA}
do-extract:
	@${DO_NADA}
.endif

do-install:
	${INSTALL_SCRIPT} ${WRKSRC}/main.py ${STAGEDIR}${PREFIX}/bin/m3utolocal
	@${MKDIR} ${STAGEDIR}${PYTHON_SITELIBDIR}
	cd ${WRKSRC} && ${COPYTREE_SHARE} m3utolocal \
		${STAGEDIR}${PYTHON_SITELIBDIR} \
		"! -name __pycache__ ! -name *.pyc ! -path */__pycache__/*"
	${INSTALL_DATA} ${WRKSRC}/utils.py ${STAGEDIR}${PYTHON_SITELIBDIR}/
	${INSTALL_DATA} ${WRKSRC}/tui.py ${STAGEDIR}${PYTHON_SITELIBDIR}/
	${INSTALL_DATA} ${WRKSRC}/download_manager.py ${STAGEDIR}${PYTHON_SITELIBDIR}/
	${INSTALL_DATA} ${WRKSRC}/downloader.py ${STAGEDIR}${PYTHON_SITELIBDIR}/
	${INSTALL_MAN} ${WRKSRC}/man/m3utolocal.1 ${STAGEDIR}${PREFIX}/share/man/man1
	@${FIND} ${STAGEDIR}${PYTHON_SITELIBDIR}/m3utolocal -type d -name __pycache__ \
		-exec ${RM} -rf {} + 2>/dev/null || ${TRUE}

.include <bsd.port.mk>
