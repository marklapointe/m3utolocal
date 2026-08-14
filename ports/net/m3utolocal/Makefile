PORTNAME=	m3utolocal
DISTVERSION=	1.2.0
CATEGORIES=	net

MAINTAINER=	mark@cloudbsd.org
COMMENT=	Search M3U playlists and download VOD files to a local library
WWW=		https://github.com/marklapointe/m3utolocal

LICENSE=	BSD2CLAUSE
LICENSE_FILE=	${WRKSRC}/LICENSE

BUILD_DEPENDS=	${PYTHON_PKGNAMEPREFIX}setuptools>=77:devel/py-setuptools@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}wheel>=0:devel/py-wheel@${PY_FLAVOR}
RUN_DEPENDS=	${PYTHON_PKGNAMEPREFIX}requests>=2.31.0:www/py-requests@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}textual>=0.80.0:textproc/py-textual@${PY_FLAVOR}

USES=		python
USE_PYTHON=	pep517 autoplist concurrent flavors

# Development: make LOCAL_SRC_PATH=/path/to/checkout -DLOCAL_SRC stage
# Release: fetch m3utolocal-1.2.0.tar.gz (see distinfo) from GitHub Releases
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

NO_ARCH=	yes
PLIST_FILES=	share/man/man1/m3utolocal.1.gz

.if defined(LOCAL_SRC) || defined(LOCAL_SRC_PATH)
do-fetch:
	@${DO_NADA}
do-extract:
	@${DO_NADA}
.endif

post-install:
	${MKDIR} ${STAGEDIR}${PREFIX}/share/man/man1
	${INSTALL_MAN} ${WRKSRC}/man/m3utolocal.1 ${STAGEDIR}${PREFIX}/share/man/man1

.include <bsd.port.mk>
