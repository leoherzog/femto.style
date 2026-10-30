import metaData from "~/data/meta";

export default function StructuredData() {
  const { defaultDescription, domain, githubRepo, siteName, versions } = metaData;
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "SoftwareSourceCode",
    url: domain,
    name: siteName,
    abstract: defaultDescription,
    isFamilyFriendly: true,
    codeRepository: githubRepo,
    version: versions.current,
    programmingLanguage: ["css", "scss"],
    keywords: [
      "css",
      "scss",
      "semantic",
      "minimal",
      "dark-theme",
      "css-framework",
      "minimalist",
      "scss-framework",
      "dark-mode",
      "minimalistic",
      "native-html",
    ],
    license: `${githubRepo}/blob/main/LICENSE.md`,
    sameAs: [githubRepo],
    image: `${domain}/opengraph.png`,
    maintainer: {
      "@type": "Person",
      name: "Leo Herzog",
      url: "https://github.com/leoherzog",
    },
    author: {
      "@type": "Person",
      name: "Leo Herzog",
      givenName: "Leo",
      familyName: "Herzog",
      url: "https://github.com/leoherzog",
    },
    isBasedOn: {
      "@type": "SoftwareSourceCode",
      name: "Pico CSS",
      url: "https://picocss.com",
      codeRepository: "https://github.com/picocss/pico",
      author: {
        "@type": "Person",
        name: "Lucas Larroche",
        url: "https://lucaslarroche.com",
      },
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
