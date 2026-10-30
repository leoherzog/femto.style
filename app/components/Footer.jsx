import { forwardRef } from "react";
import Link from "~/components/Link";
import Logo from "~/components/Logo";
import GitHubIcon from "~/components/icons/GitHub";
import NpmIcon from "~/components/icons/Npm";
import { useNavigation } from "~/contexts/NavigationContext";
import footerLinks from "~/data/footer";
import metaData from "~/data/meta";
import JsdelivrIcon from "./icons/Jsdelivr";

// Links
const Links = ({ data, ...props }) => {
  return (
    <nav className="links">
      {data.map((category, index) => {
        const { category: categoryTitle, links } = category;
        return (
          <ul key={index} {...props}>
            <li>
              <strong>{categoryTitle}</strong>
            </li>
            {links.map((link, index) => {
              const { label, url } = link;
              return (
                <li key={index}>
                  <Link to={url} className="secondary">
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        );
      })}
    </nav>
  );
};

// Build info
const BuildInfo = (props) => {
  return (
    <p className="build-info" {...props}>
      Maintained by{" "}
      <Link to="https://github.com/leoherzog" className="secondary">
        Leo Herzog
      </Link>
      , based on{" "}
      <Link to="https://picocss.com" className="secondary">
        Pico CSS
      </Link>{" "}
      by{" "}
      <Link to="https://lucaslarroche.com/" className="secondary">
        Lucas Larroche
      </Link>
      , documentation licensed{" "}
      <Link to="https://github.com/picocss/picocss.com/blob/main/LICENSE.md" className="secondary">
        CC BY-SA 4.0
      </Link>
      .
    </p>
  );
};

// Resources
const Resources = (props) => {
  const { githubRepo, npmUrl, jsDelivrUrl } = metaData;
  return (
    <ul className="resources" {...props}>
      <li>
        <Link to={githubRepo} className="contrast" title="GitHub">
          <GitHubIcon />
        </Link>
      </li>
      <li>
        <Link to={jsDelivrUrl} className="contrast" title="jsDelivr">
          <JsdelivrIcon />
        </Link>
      </li>
      <li>
        <Link to={npmUrl} className="contrast" title="NPM">
          <NpmIcon />
        </Link>
      </li>
    </ul>
  );
};

// Licenses and version
const LicensesAndVersion = () => {
  const { versions } = metaData;
  const { current } = versions;
  return (
    <>
      <p>
        Code licensed{" "}
        <Link to="https://github.com/leoherzog/femto/blob/main/LICENSE.md" className="secondary">
          MIT
        </Link>
        , docs{" "}
        <Link
          to="https://github.com/leoherzog/femto.style/blob/main/LICENSE.md"
          className="secondary"
        >
          CC BY-SA 4.0
        </Link>
        .
      </p>
      <p>
        Currently <code>v{current}</code>.
      </p>
    </>
  );
};

// Footer
export default forwardRef(function Footer(props, ref) {
  const { routePath } = useNavigation();
  if (routePath === "/demo") return null;
  return (
    <footer {...props} ref={ref}>
      <div className="container">
        <section>
          <Logo displayWordmark={false} />
          <Links data={footerLinks} />
          <BuildInfo />
          <Resources />
        </section>
        <section>
          <LicensesAndVersion />
        </section>
      </div>
    </footer>
  );
});
