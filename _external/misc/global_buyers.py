#!/c/Python314/python.exe

companies = [
    # === USA ===
    ('Uline', 'uline.com', 'USA', 'purchasing@uline.com', 'procurement@uline.com, suppliers@uline.com', '北美最大包装分销商，通过官网供应商注册系统'),
    ('The Boxery', 'theboxery.com', 'USA', 'purchasing@theboxery.com', 'info@theboxery.com', '母公司Associated Bag，可通过母公司联系'),
    ('Value Mailers', 'valuemailers.com', 'USA', 'purchasing@valuemailers.com', 'info@valuemailers.com', '专业飞机盒分销商，高度依赖中国进口'),
    ('PackagingSupplies.com', 'packagingsupplies.com', 'USA', 'purchasing@packagingsupplies.com', 'info@packagingsupplies.com', '线上包装分销商，主要从中国进货'),
    ('Grainger', 'grainger.com', 'USA', 'vendorsupport@grainger.com', 'supplierdiversity@grainger.com', '工业品MRO巨头，有供应商注册门户'),
    ('McMaster-Carr', 'mcmaster.com', 'USA', 'chi.sales@mcmaster.com', '', '已有供应商体系，较难进入'),
    ('Global Industrial', 'globalindustrial.com', 'USA', 'vendors@globalindustrial.com', 'customerservice@globalindustrial.com', '工业品分销，有纸箱品类'),
    ('Packaging Price', 'packagingprice.com', 'USA', 'sales@packagingprice.com', 'info@packagingprice.com', '在线纸箱批发，小公司'),
    ('Box Up', 'boxup.com', 'USA', 'info@boxup.com', '', '在线纸箱分销'),
    ('Paper Mart', 'papermart.com', 'USA', 'sales@papermart.com', 'info@papermart.com', '包装在线零售商'),
    ('BoxGenie', 'boxgenie.com', 'USA', 'hello@boxgenie.com', '', '在线定制纸箱平台'),
    ('Crystal Distribution', 'crystal-distribution.com', 'USA', 'info@crystal-distribution.com', '', '纸箱分销商'),
    ('Bags and Bows', 'bagsandbowsonline.com', 'USA', 'sales@bagsandbowsonline.com', '', '包装在线零售商'),
    ('Nashville Wraps', 'nashvillewraps.com', 'USA', 'info@nashvillewraps.com', '', '包装分销商'),
    # === Canada ===
    ('Nefab Canada', 'nefab.com', 'Canada', 'info.canada@nefab.com', 'info@nefab.com', '全球工业包装，加拿大有分部'),
    ('IPL Packaging', 'iplpackaging.com', 'Canada', 'info@iplpackaging.com', '', '加拿大包装分销'),
    ('Atlantic Packaging', 'atlanticpkg.com', 'Canada', 'info@atlanticpkg.com', '', '加拿大纸箱和包装分销'),
    ('Canpak', 'canpak.com', 'Canada', 'info@canpak.com', '', '加拿大包装物料分销'),
    # === UK ===
    ('DS Smith', 'dssmith.com', 'UK', 'enquiries@dssmith.com', 'procurement@dssmith.com', '欧洲最大瓦楞纸箱制造商，需要供应商注册'),
    ('Smurfit Kappa', 'smurfitkappa.com', 'UK/IE', 'info@smurfitkappa.com', 'procurement@smurfitkappa.com', '全球瓦楞包装巨头，通过官网供应商门户'),
    ('Rajapack UK', 'rajapack.co.uk', 'UK', 'export@raja.fr', 'info@rajapack.co.uk', 'Raja集团，欧洲最大包装分销商'),
    ('Kite Packaging', 'kitepackaging.co.uk', 'UK', 'enquiries@kitepackaging.co.uk', 'purchasing@kitepackaging.co.uk', '英国包装在线分销'),
    ('Davpack', 'davpack.co.uk', 'UK', 'sales@davpack.co.uk', '', '英国包装物料分销'),
    ('Boxes Direct UK', 'boxesdirect.co.uk', 'UK', 'info@boxesdirect.co.uk', '', '英国纸箱在线分销'),
    ('Presto Packaging', 'prestopackaging.co.uk', 'UK', 'info@prestopackaging.co.uk', '', '英国包装分销'),
    # === Germany ===
    ('Raja Germany', 'raja.de', 'Germany', 'info@raja.de', 'export@raja.fr', 'Raja集团德国站'),
    ('Storopack', 'storopack.com', 'Germany', 'info@storopack.com', '', '德国包装方案，有供应商注册'),
    ('Packaging24', 'packaging24.de', 'Germany', 'info@packaging24.de', '', '德国在线包装分销'),
    ('Schumacher Packaging', 'schumacher-packaging.com', 'Germany', 'info@schumacher-packaging.com', 'einkauf@schumacher-packaging.com', '德国瓦楞包装制造商，采购(einkauf)'),
    ('Kartonagen Direkt', 'kartonagen-direkt.de', 'Germany', 'info@kartonagen-direkt.de', '', '德国纸箱在线直销'),
    ('Wellpappen Shop', 'wellpappen-shop.de', 'Germany', 'info@wellpappen-shop.de', '', '德国瓦楞纸箱网店'),
    # === France ===
    ('Raja France', 'raja.fr', 'France', 'export@raja.fr', 'info@raja.fr', '法国包装分销龙头'),
    ('CG17', 'cg17.com', 'France', 'contact@cg17.com', '', '法国纸箱包装分销'),
    ('ECM Packaging', 'ecm-packaging.com', 'France', 'info@ecm-packaging.com', '', '法国包装方案'),
    ('Boites Carton', 'boites-carton.com', 'France', 'contact@boites-carton.com', '', '法国纸箱在线销售'),
    # === Australia ===
    ('Detpak', 'detpak.com', 'Australia', 'marketing@detpak.com', 'enquiries@detpak.com', '澳洲最大纸箱包装'),
    ('Packaging Supplies AU', 'packagingsupplies.com.au', 'Australia', 'sales@packagingsupplies.com.au', '', '澳洲包装在线分销'),
    ('Box Mart AU', 'boxmart.com.au', 'Australia', 'info@boxmart.com.au', '', '澳洲纸箱在线批发'),
    ('Zipbox', 'zipbox.com.au', 'Australia', 'sales@zipbox.com.au', '', '澳洲纸箱分销'),
    ('The Box Man AU', 'theboxman.com.au', 'Australia', 'sales@theboxman.com.au', '', '澳洲纸箱在线商店'),
    # === Japan ===
    ('Rengo', 'rengo.co.jp', 'Japan', 'info@rengo.co.jp', '', '日本最大瓦楞纸箱制造商'),
    ('Nippon Paper', 'nipponpapergroup.com', 'Japan', 'info@nipponpapergroup.com', '', '日本造纸及纸箱'),
    ('Oji Holdings', 'oji-holdings.com', 'Japan', 'info@oji-holdings.com', '', '日本纸业巨头'),
    # === SEA ===
    ('TGI Packaging', 'tgi-packaging.com.sg', 'Singapore', 'sales@tgi-packaging.com.sg', '', '新加坡纸箱包装'),
    ('United Bags SG', 'unitedbag.com.sg', 'Singapore', 'info@unitedbag.com.sg', '', '新加坡包装分销'),
    ('SCG Packaging', 'scgpkg.com', 'Thailand', 'info@scgpkg.com', 'procurement@scgpkg.com', '泰国最大包装集团'),
    # === Middle East ===
    ('Al Bayader International', 'albayader.com', 'UAE', 'info@albayader.com', '', '迪拜餐饮及包装分销'),
    ('Falcon Pack', 'falconpack.com', 'UAE', 'info@falconpack.com', 'sales@falconpack.com', '中东包装分销商'),
    ('Arabian Packaging', 'arabianpackaging.com', 'UAE', 'info@arabianpackaging.com', '', '阿联酋纸箱包装'),
    ('Packman Packaging', 'packmanpackaging.com', 'UAE', 'info@packmanpackaging.com', '', '迪拜包装分销'),
    ('Saudi Packaging Co.', 'saudipackaging.com', 'Saudi Arabia', 'info@saudipackaging.com', '', '沙特包装制造与分销'),
    # === Other Europe ===
    ('Viking Packaging NL', 'viking-packaging.com', 'Netherlands', 'info@viking-packaging.com', '', '荷兰包装分销'),
    ('Elk Packaging IT', 'elkpackaging.com', 'Italy', 'info@elkpackaging.com', '', '意大利包装分销'),
    ('Temafa DE', 'temafa.de', 'Germany', 'info@temafa.de', '', '德国工业包装'),
]

# Count by country
from collections import Counter
countries = Counter(c[2] for c in companies)

print('=' * 130)
print(f'{"#":3s} {"Company":30s} {"Country":15s} {"Purchasing Email":40s} {"Backup Email":35s}')
print('=' * 130)
for i, (name, domain, country, purch, backup, note) in enumerate(companies, 1):
    print(f'{i:3d} {name:30s} {country:15s} {purch:40s} {backup:35s}')

print()
print('=' * 60)
print(f'Total companies: {len(companies)}')
print(f'Countries covered: {len(countries)}')
print('Breakdown:')
for c, n in sorted(countries.items(), key=lambda x: -x[1]):
    print(f'  {c}: {n}')

# Also save to CSV
import csv
with open(r'D:\Desktop\sanyang-system\global_packaging_buyers.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['#', 'Company', 'Website', 'Country', 'Purchasing Email', 'Backup Email', 'Notes'])
    for i, (name, domain, country, purch, backup, note) in enumerate(companies, 1):
        w.writerow([i, name, f'https://www.{domain}', country, purch, backup, note])

print(f'\nCSV saved to: D:\\Desktop\\sanyang-system\\global_packaging_buyers.csv')
