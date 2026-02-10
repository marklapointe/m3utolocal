PORTNAME=	m3utolocal
DISTVERSION=	1.0.0
CATEGORIES=	net

MAINTAINER=	mark@cloudbsd.org
COMMENT=	Download files from M3U playlists based on tvg-id

LICENSE=	BSD2CLAUSE
LICENSE_FILE=	${WRKSRC}/LICENSE

RUN_DEPENDS=	${PYTHON_PKGNAMEPREFIX}requests>=2.31.0:net/py-requests@${PY_FLAVOR}

USES=		python:3.9+ shebangfix
USE_GITHUB=	yes
GH_ACCOUNT=	mlapointe
GH_PROJECT=	m3uToLocal

SHEBANG_FILES=	main.py

NO_ARCH=	yes
NO_BUILD=	yes

PLIST_FILES=	bin/m3utolocal \
		share/man/man1/m3utolocal.1.gz

do-install:
	${INSTALL_SCRIPT} ${WRKSRC}/main.py ${STAGEDIR}${PREFIX}/bin/m3utolocal
	${INSTALL_MAN} ${WRKSRC}/man/m3utolocal.1 ${STAGEDIR}${PREFIX}/share/man/man1

.include <bsd.port.mk>
