import { pathToRoot } from "../util/path"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { classNames } from "../util/lang"
import { i18n } from "../i18n"

const PageTitle: QuartzComponent = ({ fileData, cfg, displayClass }: QuartzComponentProps) => {
  const title = cfg?.pageTitle ?? i18n(cfg.locale).propertyDefaults.title
  const baseDir = pathToRoot(fileData.slug!)
  return (
    <h2 class={classNames(displayClass, "page-title")}>
      <a href={baseDir}><img class="jd-profile" src={`${baseDir}/static/profile.jpg`} alt="nqn4iwin 프로필" />{title}</a>
    </h2>
  )
}

PageTitle.css = `
.page-title {
  font-size: 1.2rem;
  margin: 0;
  font-family: var(--titleFont);
}
.page-title a {display:flex;align-items:center;gap:10px}
.jd-profile {width:38px;height:38px;object-fit:cover;object-position:33% 44%;border-radius:50%;margin:0}
`

export default (() => PageTitle) satisfies QuartzComponentConstructor
