import { QuartzComponent, QuartzComponentConstructor } from "./types"
import { pathToRoot } from "../util/path"
const EmploymentNav: QuartzComponent = ({ fileData }) => {
  const root = pathToRoot(fileData.slug!)
  const tabs = [["index", "금주의 채용공고"], ["careers-active", "진행 공고"], ["careers-closed", "마감공고(한달동안)"], ["company-research", "기업 리서치"]]
  return <nav class="employment-nav" aria-label="채용 메뉴">{tabs.map(([slug, label]) => <a class={fileData.slug === slug ? "active" : ""} href={`${root}/${slug === "index" ? "" : slug}`}>{label}</a>)}</nav>
}
EmploymentNav.css = `.employment-nav {display:flex;flex-direction:column;gap:6px;margin-top:24px}.employment-nav a{padding:10px 12px;font-weight:400;border-radius:8px;background:none}.employment-nav a.active{background:var(--highlight);font-weight:600}@media(max-width:800px){.employment-nav{flex-direction:row;flex-wrap:wrap;margin:0;gap:3px}.employment-nav a{padding:6px;font-size:.8rem}}`
export default (() => EmploymentNav) satisfies QuartzComponentConstructor
